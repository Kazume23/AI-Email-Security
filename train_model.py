"""Run in PyCharm after prepare_data.py. Uses training and validation only."""

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import tensorflow as tf
from ai_email_security.config import SETTINGS, ROOT, project_path
from ai_email_security.evaluation import choose_thresholds, evaluate_scores
from ai_email_security.text_features import PREPROCESSING_VERSION


def dataset(frame, batch_size, shuffle=False):
    data = tf.data.Dataset.from_tensor_slices(
        (frame["text"].tolist(), frame["label"].to_numpy(dtype="float32"))
    )
    if shuffle:
        data = data.shuffle(len(frame), seed=SETTINGS["training"]["seed"])
    options = tf.data.Options()
    options.threading.private_threadpool_size = 2
    return data.batch(batch_size).with_options(options).prefetch(1)


def train():
    settings = SETTINGS["training"]
    tf.config.threading.set_intra_op_parallelism_threads(settings["cpu_threads"])
    tf.config.threading.set_inter_op_parallelism_threads(2)
    tf.keras.utils.set_random_seed(settings["seed"])
    folder = project_path("data")
    manifest = json.loads((folder / "manifest.json").read_text())
    training = pd.read_json(folder / "train.jsonl", lines=True)
    validation = pd.read_json(folder / "validation.jsonl", lines=True)
    for name in ("train", "validation"):
        if (
            hashlib.sha256((folder / f"{name}.jsonl").read_bytes()).hexdigest()
            != manifest["splits"][name]["sha256"]
        ):
            raise ValueError("Dataset changed after preparation")
    vectorizer = tf.keras.layers.TextVectorization(
        max_tokens=settings["max_tokens"],
        output_sequence_length=settings["sequence_length"],
    )
    train_ds = dataset(training, settings["batch_size"], shuffle=True)
    valid_ds = dataset(validation, settings["batch_size"])
    vectorizer.adapt(train_ds.map(lambda text, label: text))
    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(), dtype=tf.string),
            vectorizer,
            tf.keras.layers.Embedding(
                settings["max_tokens"], settings["embedding_dim"], mask_zero=True
            ),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(settings["hidden_units"], activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(settings["learning_rate"]),
        loss="binary_crossentropy",
    )
    history = model.fit(
        train_ds,
        validation_data=valid_ds,
        epochs=settings["epochs"],
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=settings["patience"],
                restore_best_weights=True,
            )
        ],
        verbose=2,
    )
    scores = model.predict(valid_ds, verbose=0).ravel()
    thresholds = choose_thresholds(
        validation["label"], scores, settings["threshold_steps"]
    )
    identifier = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    bundle = project_path("models") / identifier
    bundle.mkdir(parents=True)
    target = bundle / "model.keras"
    model.save(target)
    restored = tf.keras.models.load_model(target, compile=False)
    np.testing.assert_allclose(
        model(tf.constant(validation["text"].head(5).tolist())).numpy(),
        restored(tf.constant(validation["text"].head(5).tolist())).numpy(),
        atol=1e-6,
    )
    metadata = {
        "model_id": identifier,
        "preprocessing": PREPROCESSING_VERSION,
        "dataset_id": manifest["source_sha256"],
        "manifest": manifest,
        "thresholds": thresholds,
        "settings": settings,
        "tensorflow": tf.__version__,
        "keras": tf.keras.__version__,
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "model_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "validation": evaluate_scores(validation["label"], scores, thresholds),
        "history": history.history,
    }
    (bundle / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    pointer = project_path("models") / "current.tmp"
    pointer.write_text(json.dumps({"bundle": identifier}), encoding="utf-8")
    pointer.replace(project_path("models") / "current.json")
    print(json.dumps(metadata["validation"], indent=2))
    print("Model saved:", bundle)


if __name__ == "__main__":
    train()
