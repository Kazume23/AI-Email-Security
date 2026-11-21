from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from . import __version__
from .analyzer import ENGINES, analyze_prepared
from .eml_reader import read_eml
from .ollama_client import EngineUnavailable
from .rules import find_signals


def compare(raw):
    started = perf_counter()
    mail = read_eml(raw)
    signals = find_signals(mail)
    parsing_seconds = perf_counter() - started
    results = {}
    for engine, adapter in ENGINES.items():
        timer = perf_counter()
        item = dict(
            engine=engine,
            model=adapter["model"],
            input_profile=adapter["input"],
            status="error",
            verdict=None,
            risk=None,
            score=None,
            thresholds=None,
            evidence=None,
            explanation=None,
            recommendation=None,
            limitations=None,
            truncation=None,
            error=None,
            report=None,
        )
        try:
            report = analyze_prepared(mail, signals, engine)
            diagnostics = report.get("diagnostics", {})
            item.update(
                status="success",
                model=report["model"],
                report=report,
                verdict=report["analysis"]["verdict"],
                risk=report["analysis"]["risk"],
                evidence=report["analysis"].get("evidence"),
                explanation=report["analysis"].get("explanation"),
                recommendation=report["analysis"].get("recommendation"),
                score=report.get("score"),
                thresholds=report.get("thresholds"),
                limitations=report["limitations"],
                truncation={
                    key: diagnostics.get(key)
                    for key in (
                        "tokens_before_limit",
                        "tokens_used",
                        "tokens_omitted",
                        "full_text_processed",
                    )
                }
                if "tokens_used" in diagnostics
                else None,
            )
        except Exception as exc:
            item["status"] = (
                "unavailable" if isinstance(exc, EngineUnavailable) else "error"
            )
            item["error"] = {
                "code": type(exc).__name__,
                "message": "Silnik niedostępny. Sprawdź model i usługę."
                if item["status"] == "unavailable"
                else "Analiza silnika nie została ukończona.",
            }
        item["seconds"] = perf_counter() - timer
        results[engine] = item
    successful = [item for item in results.values() if item["status"] == "success"]
    return {
        "schema_version": "comparison-v1",
        "code_version": __version__,
        "comparison_id": uuid4().hex,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "parsing_seconds": parsing_seconds,
        "total_seconds": perf_counter() - started,
        "results": results,
        "rule_signals": signals,
        "agreement": len({item["verdict"] for item in successful}) == 1
        if len(successful) == len(results) and len(results) > 1
        else None,
        "comparison_scope": "existing_systems_different_inputs",
    }
