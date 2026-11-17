import hashlib
import json
import urllib.request

import pandas as pd

from ai_email_security.config import project_path


def audit():
    record = "18471483"
    filename = "meajor_cleaned_preprocessed.parquet.gzip"
    folder = project_path("data") / "candidates" / record
    folder.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(
        f"https://zenodo.org/api/records/{record}", timeout=60
    ) as response:
        metadata = json.load(response)
    source = next(item for item in metadata["files"] if item["key"] == filename)
    path = folder / filename
    if not path.exists():
        temporary = path.with_suffix(".part")
        with (
            urllib.request.urlopen(source["links"]["self"], timeout=120) as response,
            temporary.open("wb") as stream,
        ):
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        temporary.replace(path)
    algorithm, expected = source["checksum"].split(":")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, algorithm).hexdigest()
    if actual != expected:
        raise ValueError("Candidate checksum mismatch")
    frame = pd.read_parquet(path)
    report = {
        "record": record,
        "license": metadata["metadata"].get("license"),
        "checksum": source["checksum"],
        "rows": len(frame),
        "columns": list(frame.columns),
        "status": "candidate_only_not_approved_for_training",
    }
    for column in ("source", "label"):
        if column in frame:
            report[column] = {
                str(key): int(value)
                for key, value in frame[column].value_counts(dropna=False).items()
            }
    if {"source", "label"}.issubset(frame.columns):
        report["source_label"] = {
            str(key): int(value)
            for key, value in frame.groupby(["source", "label"]).size().items()
        }
    (folder / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    audit()
