import hashlib
import json
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors
from ai_email_security.config import project_path
from ai_email_security.text_features import prepare_text
from build_corpus import normalized_template


def prepare(audit_only=True):
    folder = project_path("data") / "v030"
    old = pd.read_csv(project_path("data") / "reviewed.csv").fillna("")
    old["text"] = [prepare_text(s, b) for s, b in zip(old["subject"], old["body"])]
    old["origin"] = "old"
    new = pd.read_csv(folder / "external.csv").rename(columns={"Email Text": "text"})
    new["label"] = new["Email Type"].map({"Safe Email": 0, "Phishing Email": 1})
    new["origin"] = "new"
    new["source"] = "zenodo13474746"
    external = pd.read_json(folder / "independent.jsonl", lines=True)
    external["text"] = [
        prepare_text(s, b) for s, b in zip(external["subject"], external["body"])
    ]
    external["label"] = external["label"].map({"phishing": 1, "benign": 0})
    external["origin"] = "independent"
    external["source"] = "SunnyThakur25"
    combined = pd.concat([old, new, external], ignore_index=True)[
        ["text", "label", "origin", "source"]
    ]
    combined["text"] = combined["text"].map(lambda text: prepare_text("", text))
    combined["digest"] = (
        combined["text"]
        .str.lower()
        .map(lambda text: hashlib.sha256(text.encode()).hexdigest())
    )
    vectors = TfidfVectorizer(max_features=20000, ngram_range=(1, 2)).fit_transform(
        combined["text"].map(normalized_template)
    )
    graph = (
        NearestNeighbors(metric="cosine", radius=0.15, n_jobs=2)
        .fit(vectors)
        .radius_neighbors_graph(vectors, mode="connectivity")
    )
    _, combined["group"] = connected_components(graph, directed=False)
    conflicting = combined.groupby("group")["label"].nunique()
    combined = combined[~combined["group"].isin(conflicting[conflicting > 1].index)]
    old_groups = set(combined.loc[combined["origin"] == "old", "group"])
    new = (
        combined[(combined["origin"] == "new") & ~combined["group"].isin(old_groups)]
        .drop_duplicates("digest")
        .copy()
    )
    external = combined[
        (combined["origin"] == "independent")
        & ~combined["group"].isin(old_groups | set(new["group"]))
    ].drop_duplicates("digest")
    audit = {
        "new_unique": len(new),
        "independent_unique": len(external),
        "new_classes": new["label"].value_counts().to_dict(),
        "independent_classes": external["label"].value_counts().to_dict(),
        "source_class_counts": combined.groupby(["source", "label"]).size().to_dict(),
    }
    audit["source_class_counts"] = {
        str(key): int(value) for key, value in audit["source_class_counts"].items()
    }
    (folder / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if audit_only:
        print(
            "Audit only: these small candidate datasets are not approved for training."
        )
        return
    if new["label"].nunique() != 2 or external["label"].nunique() != 2:
        raise ValueError(
            "Independent data with both classes unavailable after leakage audit"
        )
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    new["fold"] = -1
    for fold, (_, indices) in enumerate(
        splitter.split(new, new["label"], new["group"])
    ):
        new.iloc[indices, new.columns.get_loc("fold")] = fold
    old_train = pd.read_json(project_path("data") / "train.jsonl", lines=True)
    old_train["source"] = "legacy-training"
    splits = {
        "train": pd.concat([old_train, new[new["fold"] < 3]], ignore_index=True),
        "validation": new[new["fold"] == 3],
        "test": new[new["fold"] == 4],
        "independent": external,
    }
    manifest = {}
    for name, frame in splits.items():
        if frame["label"].nunique() != 2:
            raise ValueError(f"Split {name} lacks both classes")
        path = folder / f"{name}.jsonl"
        frame.to_json(path, orient="records", lines=True, force_ascii=False)
        manifest[name] = {
            "count": len(frame),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    prepare()
