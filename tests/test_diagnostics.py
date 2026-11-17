import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tensorflow as tf

from ai_email_security import keras_diagnostics as diagnostic
from ai_email_security.analyzer import analyze
from ai_email_security.keras_client import analyze_with_keras
from ai_email_security.model_layers import build_classifier
from ai_email_security.ollama_client import AnalysisError


def bundle(architecture='average'):
    vectorizer = tf.keras.layers.TextVectorization(max_tokens=20, output_sequence_length=4, vocabulary=['hello', 'friend', 'pay', 'now'])
    model = build_classifier(vectorizer, architecture, {'max_tokens': 20, 'embedding_dim': 4, 'hidden_units': 4})
    return model, {'model_id': 'synthetic', 'model_sha256': 'synthetic-hash', 'preprocessing': 'subject-body-v1', 'dataset_id': 'synthetic-data', 'thresholds': {'low': 0.2, 'high': 0.8}}


def mail():
    return {'headers': {'Subject': 'Hello'}, 'text': 'Friend. Pay now!'}


class DiagnosticsTests(unittest.TestCase):
    def test_exact_tokens_oov_truncation_and_empty(self):
        model, _ = bundle()
        stats = diagnostic.input_stats(model, 'HELLO, friend! mystery pay now')
        self.assertEqual(stats['tokens_before_limit'], 5)
        self.assertEqual(stats['tokens_used'], 4)
        self.assertEqual(stats['tokens_omitted'], 1)
        self.assertEqual(stats['oov_count'], 1)
        self.assertEqual(stats['oov_fraction'], 0.2)
        self.assertEqual(diagnostic.input_stats(model, '')['tokens_used'], 0)
        self.assertEqual(diagnostic.input_stats(model, 'hello ' * 10000)['tokens_omitted'], 9996)

    def test_same_prediction_and_weights_with_diagnostics(self):
        for architecture in ('average', 'conv1d'):
            model, metadata = bundle(architecture)
            before = [value.copy() for value in model.get_weights()]
            with patch('ai_email_security.keras_client.load_bundle', return_value=(model, metadata)):
                with patch.object(diagnostic, 'options', return_value={'enabled': False}):
                    _, plain = analyze_with_keras(mail())
                with patch.object(diagnostic, 'options', return_value={'enabled': True}):
                    _, detailed = analyze_with_keras(mail())
                    result = diagnostic.influence(mail(), 'synthetic', detailed['score'])
            self.assertEqual(plain['score'], detailed['score'])
            self.assertEqual(detailed['diagnostics']['architecture'], architecture)
            self.assertEqual(detailed['diagnostics']['thresholds'], metadata['thresholds'])
            self.assertEqual(result['variants_evaluated'], 3)
            for row in result['fragments']:
                self.assertAlmostEqual(row['delta'], row['score_without'] - detailed['score'])
            for old, new in zip(before, model.get_weights()):
                np.testing.assert_array_equal(old, new)

    def test_privacy_and_errors_in_log(self):
        model, metadata = bundle()
        with tempfile.TemporaryDirectory() as folder, patch.object(diagnostic, 'project_path', return_value=Path(folder)), patch('ai_email_security.keras_client.load_bundle', return_value=(model, metadata)):
            report = analyze(b'Subject: hello\nFrom: secret@example.org\n\nfriend private-secret https://secret.invalid', engine='keras')
            log = (Path(folder) / 'diagnostics/analyses.jsonl').read_text(encoding='utf-8')
            for private in ('secret@example.org', 'private-secret', 'https://secret.invalid'):
                self.assertNotIn(private, log)
            parsed = json.loads(log)
            self.assertEqual(parsed['verdict'], report['analysis']['verdict'])
            self.assertEqual(parsed['thresholds'], report['thresholds'])
            with patch('ai_email_security.keras_client.load_bundle', side_effect=AnalysisError('PRIVATE PATH')):
                with self.assertRaises(AnalysisError):
                    analyze(b'Subject: hello\n\nfriend', engine='keras')
            log = (Path(folder) / 'diagnostics/analyses.jsonl').read_text(encoding='utf-8')
            self.assertNotIn('PRIVATE PATH', log)
            self.assertEqual(json.loads(log.splitlines()[-1])['status'], 'error')

    def test_limits_disabled_and_wrong_model(self):
        model, metadata = bundle()
        score = float(model(tf.constant(['Hello Friend. Pay now!'])).numpy().ravel()[0])
        with patch('ai_email_security.keras_client.load_bundle', return_value=(model, metadata)):
            with patch.object(diagnostic, 'options', return_value={'max_fragments': 1}):
                result = diagnostic.influence(mail(), 'synthetic', score)
                self.assertEqual(result['variants_evaluated'], 1)
                self.assertEqual(result['fragments'][0]['kind'], 'subject')
            with self.assertRaises(AnalysisError):
                diagnostic.influence(mail(), 'different', score)
            with patch.object(diagnostic, 'options', return_value={'text_influence_enabled': False}):
                with self.assertRaises(AnalysisError):
                    diagnostic.influence(mail(), 'synthetic', score)

    def test_rotation_and_private_rule_names(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(diagnostic, 'project_path', return_value=Path(folder)), patch.object(diagnostic, 'options', return_value={'log_max_bytes': 100, 'log_backups': 2}):
            for _ in range(10):
                diagnostic.write_log(diagnostic.new_record())
            self.assertLessEqual(len(list((Path(folder) / 'diagnostics').iterdir())), 3)
        summary = diagnostic.rule_summary(['Potencjalnie ryzykowne rozszerzenie załącznika: private.exe'])
        self.assertNotIn('private.exe', json.dumps(summary))
