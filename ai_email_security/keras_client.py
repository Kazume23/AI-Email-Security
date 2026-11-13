"""Load one immutable model bundle once per process."""

import hashlib
import json
import math
from functools import lru_cache
from .config import project_path
from .evaluation import classify_score
from .ollama_client import AnalysisError
from .text_features import PREPROCESSING_VERSION, mail_text


@lru_cache(maxsize=1)
def load_bundle():
    try:
        import tensorflow as tf

        folder = project_path("models")
        pointer = json.loads((folder / "current.json").read_text(encoding="utf-8"))
        bundle = folder / pointer["bundle"]
        if bundle.parent.resolve() != folder.resolve():
            raise ValueError("Invalid model bundle path")
        metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
        if metadata["preprocessing"] != PREPROCESSING_VERSION:
            raise ValueError("Incompatible preprocessing")
        thresholds = metadata["thresholds"]
        if not 0 <= thresholds["low"] < thresholds["high"] <= 1:
            raise ValueError("Invalid thresholds")
        model_path = bundle / "model.keras"
        with model_path.open("rb") as stream:
            if (
                hashlib.file_digest(stream, "sha256").hexdigest()
                != metadata["model_sha256"]
            ):
                raise ValueError("Model checksum mismatch")
        model = tf.keras.models.load_model(model_path, compile=False, safe_mode=True)
        return model, metadata
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        raise AnalysisError(
            "Model Keras jest niedostępny lub niezgodny. Uruchom train_model.py, następnie ponownie aplikację."
        ) from exc


def analyze_with_keras(mail):
    model, metadata = load_bundle()
    try:
        import tensorflow as tf

        score = float(
            model(tf.constant([mail_text(mail)]), training=False).numpy().ravel()[0]
        )
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid score")
    except (ValueError, TypeError, RuntimeError) as exc:
        raise AnalysisError("Model Keras nie ukończył analizy.") from exc
    verdict, risk = classify_score(score, metadata["thresholds"])
    recommendations = {
        "safe": "Zachowaj ostrożność przy udostępnianiu danych i otwieraniu załączników.",
        "suspicious": "Zweryfikuj prośbę przez znany, niezależny kanał kontaktu.",
        "dangerous": "Wstrzymaj działanie i zweryfikuj wiadomość z nadawcą przez niezależny kanał.",
    }
    result = {
        "verdict": verdict,
        "risk": risk,
        "evidence": [],
        "explanation": "Klasyfikacja na podstawie tematu i treści. Model Keras nie wyznacza przyczyn dla pojedynczych fragmentów tekstu.",
        "recommendation": recommendations[verdict],
    }
    details = {
        "model": metadata["model_id"],
        "score": score,
        "thresholds": metadata["thresholds"],
        "dataset_id": metadata["dataset_id"],
    }
    return result, details
