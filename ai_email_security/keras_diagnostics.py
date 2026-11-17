import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from time import perf_counter

import numpy as np

from .config import SETTINGS, project_path
from .text_features import mail_text, prepare_text

LOCK = threading.Lock()


def options():
    return SETTINGS.get('diagnostics', {})


def new_record():
    return {'analysis_id': uuid.uuid4().hex, 'started_at': datetime.now(timezone.utc).isoformat()}


def write_log(record):
    if not options().get('enabled', True) or not options().get('save_logs', True):
        return
    try:
        with LOCK:
            folder = project_path('reports') / 'diagnostics'
            folder.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(folder / 'analyses.jsonl', maxBytes=options().get('log_max_bytes', 1048576), backupCount=options().get('log_backups', 3), encoding='utf-8')
            logger = logging.Logger('email_security.diagnostics', level=logging.INFO)
            logger.propagate = False
            logger.addHandler(handler)
            try:
                logger.info(json.dumps(record, ensure_ascii=False, allow_nan=False))
            finally:
                handler.close()
    except (OSError, ValueError):
        record['logging_error'] = 'diagnostic_log_unavailable'


def error_record(record, exc, started):
    causes = []
    while exc is not None:
        causes.append(type(exc).__name__)
        exc = exc.__cause__
    record.update(status='error', error_types=causes, total_seconds=perf_counter() - started)
    write_log(record)


@lru_cache(maxsize=4)
def tokenizers(model):
    import tensorflow as tf

    layers = [layer for layer in model.layers if isinstance(layer, tf.keras.layers.TextVectorization)]
    if len(layers) != 1:
        raise ValueError('Expected one TextVectorization layer')
    original = layers[0]
    config = original.get_config()
    if config['output_mode'] != 'int':
        raise ValueError('Expected integer token IDs')
    config.update(output_sequence_length=None, ragged=False, vocabulary=None)
    full = tf.keras.layers.TextVectorization.from_config(config)
    full.set_vocabulary(original.get_vocabulary())
    return original, full


def input_stats(model, text):
    import tensorflow as tf

    original, full = tokenizers(model)
    tensor = tf.constant([text])
    all_ids = full(tensor).numpy().ravel()
    used_ids = original(tensor).numpy().ravel()
    all_ids = all_ids[all_ids != 0]
    used_ids = used_ids[used_ids != 0]
    count, used = len(all_ids), len(used_ids)
    oov = int(np.count_nonzero(all_ids == 1))
    used_oov = int(np.count_nonzero(used_ids == 1))
    return {'tokens_before_limit': count, 'token_limit': original.get_config()['output_sequence_length'],
            'tokens_used': used, 'tokens_omitted': count - used, 'oov_count': oov,
            'oov_fraction': oov / count if count else 0.0,
            'used_oov_count': used_oov, 'used_oov_fraction': used_oov / used if used else 0.0,
            'full_text_processed': used == count}


def describe(model, metadata, mail):
    names = {type(layer).__name__ for layer in model.layers}
    architecture = 'conv1d' if names & {'MaskedConvPool', 'Conv1D'} else 'average' if 'GlobalAveragePooling1D' in names else 'unknown'
    return {'model_id': metadata['model_id'], 'model_sha256': metadata['model_sha256'],
            'experiment_id': metadata.get('experiment_id'), 'architecture': architecture,
            'preprocessing': metadata['preprocessing'], 'dataset_id': metadata.get('dataset_id'),
            'subject_chars': len(mail['headers']['Subject']), 'body_chars': len(mail['text']),
            **input_stats(model, mail_text(mail))}


def rule_summary(signals):
    return {'reply_to_mismatch': sum(s.startswith('Adres Reply-To') for s in signals),
            'risky_attachment_extension': sum(s.startswith('Potencjalnie ryzykowne') for s in signals),
            'count': len(signals), 'affects_network_score': False}


def influence(mail, expected_model, expected_score):
    import tensorflow as tf
    from .keras_client import load_bundle
    from .ollama_client import AnalysisError

    if not options().get('enabled', True) or not options().get('text_influence_enabled', True):
        raise AnalysisError('Analiza wpływu fragmentów jest wyłączona.')
    model, metadata = load_bundle()
    if metadata['model_id'] != expected_model:
        raise AnalysisError('Załadowany model zmienił się. Ponownie przeanalizuj wiadomość.')
    started = perf_counter()
    subject, body = mail['headers']['Subject'], mail['text']
    baseline = float(model(tf.constant([mail_text(mail)]), training=False).numpy().ravel()[0])
    if not np.isfinite(baseline) or not np.isclose(baseline, expected_score, atol=1e-6, rtol=0):
        raise AnalysisError('Wynik nie odpowiada wcześniejszej analizie. Przeanalizuj wiadomość ponownie.')
    fragments = []
    if subject.strip():
        fragments.append({'kind': 'subject', 'fragment': subject, 'text': prepare_text('', body)})
    matches = list(re.finditer(r'[^.!?\n]+(?:[.!?]+|$)', body))
    limit = max(0, min(int(options().get('max_fragments', 30)), 200))
    total = len(fragments) + sum(bool(m.group().strip()) for m in matches)
    for match in matches:
        if len(fragments) >= limit:
            break
        if match.group().strip():
            fragments.append({'kind': 'body', 'fragment': match.group().strip(),
                              'text': prepare_text(subject, body[:match.start()] + body[match.end():])})
    fragments = fragments[:limit]
    batch_size = max(1, min(int(options().get('batch_size', 16)), 64))
    rows = []
    for start in range(0, len(fragments), batch_size):
        batch = fragments[start:start + batch_size]
        scores = model(tf.constant([item['text'] for item in batch]), training=False).numpy().ravel()
        for item, value in zip(batch, scores):
            finite = bool(np.isfinite(value))
            rows.append({'kind': item['kind'], 'fragment': item['fragment'],
                         'score_without': float(value) if finite else None,
                         'delta': float(value) - baseline if finite else None,
                         'status': 'ok' if finite else 'nonfinite_empty_or_unsupported_input'})
    rows.sort(key=lambda item: abs(item['delta']) if item['delta'] is not None else -1, reverse=True)
    return {'model_id': metadata['model_id'], 'baseline_score': baseline, 'fragments': rows,
            'variants_evaluated': len(rows), 'fragments_available': total,
            'fragments_skipped': total - len(rows), 'seconds': perf_counter() - started,
            'method': 'leave_one_fragment_out',
            'limitations': 'Analiza wrażliwości, nie dowód przyczyny phishingu. Delta = wynik po usunięciu minus wynik oryginalny. Usunięcie tekstu może przesunąć inne tokeny do okna modelu. Fragmenty poza limitem mogą nie zmieniać wyniku.'}
