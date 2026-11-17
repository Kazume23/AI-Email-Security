import tempfile
import unittest
from pathlib import Path
import numpy as np
import tensorflow as tf
from ai_email_security.model_layers import MaskedConvPool, build_classifier


class ConvTests(unittest.TestCase):
    def test_padding_and_short_input(self):
        layer = MaskedConvPool(4, 3)
        embeddings = tf.ones((1, 3, 2))
        expected = layer([embeddings, tf.constant([[1, 2, 3]])])
        actual = layer([tf.pad(embeddings, [[0, 0], [0, 4], [0, 0]]), tf.constant([[1, 2, 3, 0, 0, 0, 0]])])
        np.testing.assert_allclose(expected, actual)
        empty = layer([tf.ones((1, 2, 2)), tf.constant([[1, 2]])])
        np.testing.assert_array_equal(empty, np.zeros((1, 4)))

    def test_serialization(self):
        vectorizer = tf.keras.layers.TextVectorization(max_tokens=20, output_sequence_length=8, vocabulary=['hello', 'world', 'friend'])
        model = build_classifier(vectorizer, 'conv1d', {'max_tokens': 20, 'embedding_dim': 4, 'hidden_units': 4})
        text = tf.constant(['hello world friend'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.keras'
            model.save(path)
            restored = tf.keras.models.load_model(path, compile=False)
            np.testing.assert_allclose(model(text), restored(text), atol=1e-6)
