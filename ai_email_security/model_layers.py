import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package="email_security")
class MaskedConvPool(tf.keras.layers.Layer):
    def __init__(self, filters=64, kernel_size=3, **kwargs):
        super().__init__(**kwargs)
        self.filters = filters
        self.kernel_size = kernel_size
        self.convolution = tf.keras.layers.Conv1D(
            filters, kernel_size, activation="relu", padding="valid"
        )

    def build(self, input_shape):
        embedding_shape = list(input_shape[0])
        embedding_shape[1] = None
        self.convolution.build(tuple(embedding_shape))
        super().build(input_shape)

    def call(self, inputs):
        embeddings, tokens = inputs
        extra = tf.maximum(self.kernel_size - tf.shape(tokens)[1], 0)
        embeddings = tf.pad(embeddings, [[0, 0], [0, extra], [0, 0]])
        tokens = tf.pad(tokens, [[0, 0], [0, extra]])
        features = self.convolution(embeddings)
        valid_tokens = tf.cast(tokens != 0, features.dtype)[..., None]
        counts = tf.nn.conv1d(
            valid_tokens,
            tf.ones((self.kernel_size, 1, 1), dtype=features.dtype),
            stride=1,
            padding="VALID",
        )
        valid_windows = counts == self.kernel_size
        masked = tf.where(valid_windows, features, tf.cast(-1e30, features.dtype))
        pooled = tf.reduce_max(masked, axis=1)
        return tf.where(
            tf.reduce_any(valid_windows, axis=1), pooled, tf.zeros_like(pooled)
        )

    def get_config(self):
        return {
            **super().get_config(),
            "filters": self.filters,
            "kernel_size": self.kernel_size,
        }


def build_classifier(vectorizer, architecture, settings):
    text = tf.keras.Input(shape=(), dtype=tf.string)
    tokens = vectorizer(text)
    embeddings = tf.keras.layers.Embedding(
        settings["max_tokens"],
        settings["embedding_dim"],
        mask_zero=architecture == "average",
    )(tokens)
    if architecture == "conv1d":
        features = MaskedConvPool(
            settings.get("conv_filters", 64), settings.get("conv_kernel", 3)
        )([embeddings, tokens])
    elif architecture == "average":
        features = tf.keras.layers.GlobalAveragePooling1D()(embeddings)
    else:
        raise ValueError("Unknown architecture")
    hidden = tf.keras.layers.Dense(settings["hidden_units"], activation="relu")(
        features
    )
    output = tf.keras.layers.Dense(1, activation="sigmoid")(hidden)
    return tf.keras.Model(text, output)
