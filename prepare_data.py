import hashlib
import json
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from ai_email_security.config import SETTINGS, project_path
from ai_email_security.text_features import prepare_text


def prepare():
    folder = project_path("data")
    source = folder / "reviewed.csv"
    frame = pd.read_csv(source).fillna("")
    if not {"subject", "body", "label", "group"} <= set(frame.columns):
        raise ValueError("CSV requires subject, body, label, group columns.")
    if not set(frame["label"].unique()) <= {0, 1}:
        raise ValueError("Labels must be 0 or 1.")
    frame["text"] = [
        prepare_text(s, b) for s, b in zip(frame["subject"], frame["body"])
    ]
    frame = frame[
        frame["text"].str.len().between(20, SETTINGS["limits"]["text_chars"])
    ].copy()
    frame["digest"] = (
        frame["text"]
        .str.lower()
        .map(lambda text: hashlib.sha256(text.encode()).hexdigest())
    )
    conflicts = frame.groupby("digest")["label"].nunique()
    frame = frame[
        ~frame["digest"].isin(conflicts[conflicts > 1].index)
    ].drop_duplicates("digest")
    frame["group"] = frame["group"].astype(str)
    if (frame["group"].str.len() == 0).any():
        raise ValueError("Every record requires a campaign/template group.")
    splitter = StratifiedGroupKFold(
        n_splits=20, shuffle=True, random_state=SETTINGS["training"]["seed"]
    )
    frame["fold"] = -1
    for fold, (_, indexes) in enumerate(
        splitter.split(frame, frame["label"], frame["group"])
    ):
        frame.iloc[indexes, frame.columns.get_loc("fold")] = fold
    partitions = {
        "train": frame[frame["fold"] < 14],
        "validation": frame[frame["fold"].between(14, 16)],
        "test": frame[frame["fold"] >= 17],
    }
    metadata = {
        "seed": SETTINGS["training"]["seed"],
        "requested_ratios": [0.7, 0.15, 0.15],
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "splits": {},
    }
    for name, subset in partitions.items():
        if subset["label"].nunique() != 2:
            raise ValueError(f"Both classes required in {name}")
        target = folder / f"{name}.jsonl"
        subset[["text", "label", "group", "digest"]].to_json(
            target, orient="records", lines=True, force_ascii=False
        )
        metadata["splits"][name] = {
            "count": len(subset),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    (folder / "manifest.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    prepare()
