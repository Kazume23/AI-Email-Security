import csv
import hashlib
import json
import statistics
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .analyzer import ENGINES
from .comparison import compare
from .config import ROOT, SETTINGS, project_path


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(rows):
    engines = {}
    for name in ENGINES:
        items = [(row["label"], row["results"][name]) for row in rows]
        valid = [(label, item) for label, item in items if item["status"] == "success"]
        tp = sum(label == 1 and item["verdict"] != "safe" for label, item in valid)
        fp = sum(label == 0 and item["verdict"] != "safe" for label, item in valid)
        fn = sum(label == 1 and item["verdict"] == "safe" for label, item in valid)
        tn = sum(label == 0 and item["verdict"] == "safe" for label, item in valid)
        times = [item["seconds"] for _, item in items if item["seconds"] is not None]
        engines[name] = {
            "count": len(items),
            "success": len(valid),
            "coverage": ratio(len(valid), len(items)),
            "errors": sum(item["status"] == "error" for _, item in items),
            "unavailable": sum(item["status"] == "unavailable" for _, item in items),
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
            "fpr": ratio(fp, fp + tn),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "first_seconds": times[0] if times else None,
            "mean_seconds": statistics.mean(times) if times else None,
            "median_seconds": statistics.median(times) if times else None,
        }
    agreements = [row["agreement"] for row in rows if row["agreement"] is not None]
    return {
        "count": len(rows),
        "engines": engines,
        "agreement_count": sum(agreements),
        "agreement_denominator": len(agreements),
        "agreement_rate": ratio(sum(agreements), len(agreements)),
        "input_errors": sum(row.get("input_error") is not None for row in rows),
    }


def read_manifest(path):
    cases, identifiers = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("id"), str)
            or not case["id"].strip()
        ):
            raise ValueError("Each case requires a nonempty string ID")
        if case["id"] in identifiers:
            raise ValueError("Duplicate case ID")
        if type(case.get("label")) is not int or case["label"] not in (0, 1):
            raise ValueError("Each case requires label 0 or 1")
        if not isinstance(case.get("path"), str) or not case["path"]:
            raise ValueError("Each case requires an EML path")
        for key in ("source", "category"):
            if case.get(key) is not None and not isinstance(case[key], str):
                raise ValueError("Source and category must be strings")
        identifiers.add(case["id"])
        cases.append(case)
    if not cases:
        raise ValueError("Empty manifest")
    return cases


def technical_result(item, label):
    result = {
        key: item.get(key)
        for key in (
            "engine",
            "model",
            "input_profile",
            "status",
            "verdict",
            "risk",
            "score",
            "thresholds",
            "seconds",
            "truncation",
        )
    }
    result["error_code"] = item["error"]["code"] if item.get("error") else None
    result["correct"] = (
        (int(item["verdict"] != "safe") == label)
        if item["status"] == "success"
        else None
    )
    diagnostics = (item.get("report") or {}).get("diagnostics", {})
    result["model_sha256"] = diagnostics.get("model_sha256")
    result["dataset_id"] = (item.get("report") or {}).get("dataset_id")
    return result


def git_state():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        diff = subprocess.check_output(
            ["git", "diff", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return {
            "commit": commit,
            "dirty": bool(status),
            "diff_sha256": hashlib.sha256(diff).hexdigest(),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None, "diff_sha256": None}


def run_experiment(manifest, dataset_kind, limit=10):
    if (
        dataset_kind not in ("demonstration", "independent")
        or type(limit) is not int
        or limit < 1
    ):
        raise ValueError("Choose dataset kind and a positive limit")
    manifest = Path(manifest).resolve()
    cases = read_manifest(manifest)
    selected = cases[:limit]
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    folder = project_path("reports") / "experiments" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    metadata = {
        "run_id": run_id,
        "dataset_kind": dataset_kind,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "manifest_count": len(cases),
        "requested_limit": limit,
        "selected_count": len(selected),
        "selected_ids": [case["id"] for case in selected],
        "code": git_state(),
        "configuration": SETTINGS,
        "engine_order": list(ENGINES),
        "input_profiles": {name: adapter["input"] for name, adapter in ENGINES.items()},
        "status": "running",
        "comparison_scope": "existing_systems_different_inputs",
    }
    (folder / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    rows = []
    fields = [
        "id",
        "label",
        "source",
        "category",
        "engine",
        "model",
        "status",
        "verdict",
        "score",
        "seconds",
        "correct",
        "error_code",
    ]
    with (
        (folder / "cases.jsonl").open("x", encoding="utf-8") as stream,
        (folder / "cases.csv").open("x", newline="", encoding="utf-8") as table,
    ):
        writer = csv.DictWriter(table, fieldnames=fields)
        writer.writeheader()
        for case in selected:
            row = {key: case.get(key) for key in ("id", "label", "source", "category")}
            row.update(
                input_sha256=None,
                input_error=None,
                parsing_seconds=None,
                total_seconds=None,
            )
            try:
                raw = (manifest.parent / case["path"]).read_bytes()
                row["input_sha256"] = hashlib.sha256(raw).hexdigest()
                report = compare(raw)
                row.update(
                    agreement=report["agreement"],
                    parsing_seconds=report["parsing_seconds"],
                    total_seconds=report["total_seconds"],
                    results={
                        name: technical_result(item, case["label"])
                        for name, item in report["results"].items()
                    },
                )
            except Exception as exc:
                row.update(
                    input_error=type(exc).__name__,
                    agreement=None,
                    results={
                        name: {
                            "engine": name,
                            "status": "error",
                            "verdict": None,
                            "seconds": None,
                            "correct": None,
                            "error_code": "input_error",
                        }
                        for name in ENGINES
                    },
                )
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            for name, item in row["results"].items():
                values = {**row, **item, "engine": name}
                writer.writerow({key: values.get(key) for key in fields})
            table.flush()
            rows.append(row)
            (folder / "summary.json").write_text(
                json.dumps({"dataset_kind": dataset_kind, **summarize(rows)}, indent=2),
                encoding="utf-8",
            )
    metadata["status"] = "completed"
    (folder / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return folder
