from datetime import datetime, timezone
from . import __version__
from .eml_reader import read_eml
from .rules import find_signals
from .ollama_client import analyze_with_model, MODEL


def analyze(raw, engine="qwen"):
    if engine not in ("qwen", "keras"):
        raise ValueError("Unknown analysis engine")
    mail = read_eml(raw)
    signals = find_signals(mail)
    details = {"model": MODEL}
    if engine == "keras":
        from .keras_client import analyze_with_keras

        result, details = analyze_with_keras(mail)
    else:
        result = analyze_with_model(mail, signals)
    return {
        "version": __version__,
        "engine": engine,
        **details,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "analysis": result,
        "rule_signals": signals,
        "limitations": "Ocena modelu, nie prawdopodobieństwo. Brak wykrytych sygnałów nie gwarantuje bezpieczeństwa. Nie skanowano zawartości załączników ani stron docelowych.",
    }
