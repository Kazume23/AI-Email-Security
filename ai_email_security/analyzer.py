from datetime import datetime, timezone
from time import perf_counter
from . import __version__
from .eml_reader import read_eml
from .rules import find_signals
from .ollama_client import analyze_with_model, MODEL


def analyze(raw, engine="qwen"):
    if engine not in ENGINES:
        raise ValueError("Unknown analysis engine")
    mail = read_eml(raw)
    return analyze_prepared(mail, find_signals(mail), engine)


def analyze_prepared(mail, signals, engine):
    if engine == "keras":
        from .keras_diagnostics import (
            new_record,
            options,
            write_log,
            error_record,
            rule_summary,
        )

        if options().get("enabled", True):
            started = perf_counter()
            record = new_record()
            try:
                report = _analyze(mail, signals, engine)
            except Exception as exc:
                error_record(record, exc, started)
                raise
            diagnostics = report.get("diagnostics", {})
            diagnostics.update(record)
            diagnostics.update(
                total_seconds=perf_counter() - started,
                rule_summary=rule_summary(report["rule_signals"]),
            )
            diagnostics.setdefault("status", "ok")
            report["diagnostics"] = diagnostics
            write_log(diagnostics)
            return report
    return _analyze(mail, signals, engine)


def qwen_adapter(mail, signals):
    return analyze_with_model(mail, signals), {"model": MODEL}


def keras_adapter(mail, signals):
    from .keras_client import analyze_with_keras

    return analyze_with_keras(mail)


ENGINES = {
    "keras": {"run": keras_adapter, "input": "subject_body", "model": None},
    "qwen": {"run": qwen_adapter, "input": "email_metadata_rules", "model": MODEL},
}


def _analyze(mail, signals, engine):
    result, details = ENGINES[engine]["run"](mail, signals)
    return {
        "version": __version__,
        "engine": engine,
        **details,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "analysis": result,
        "rule_signals": signals,
        "limitations": "Ocena modelu, nie prawdopodobieństwo. Brak wykrytych sygnałów nie gwarantuje bezpieczeństwa. Nie skanowano zawartości załączników ani stron docelowych.",
    }
