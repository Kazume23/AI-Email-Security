"""Select phishing sources and ham only, then group near-duplicate templates."""

import json
import re
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from ai_email_security.config import SETTINGS, project_path
from ai_email_security.text_features import prepare_text


def normalized_template(text):
    text = re.sub(r"https?://\S+|\S+@\S+", " entity ", text.lower())
    return re.sub(r"\d+|[^a-z\s]", " ", text)


def build():
    folder = project_path("data")
    frames = []
    for name in SETTINGS["dataset"]["files"]:
        frame = pd.read_csv(folder / "raw" / name).fillna("")
        expected = 0 if name == "SpamAssasin.csv" else 1
        frame = frame[frame["label"] == expected][["subject", "body", "label"]].copy()
        frame["source"] = name
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined["text"] = [
        prepare_text(s, b) for s, b in zip(combined["subject"], combined["body"])
    ]
    combined = combined[
        combined["text"].str.len().between(20, SETTINGS["limits"]["text_chars"])
    ]
    combined["normalized"] = (
        combined["text"].str.lower().str.replace(r"\s+", " ", regex=True)
    )
    conflicts = combined.groupby("normalized")["label"].nunique()
    combined = combined[
        ~combined["normalized"].isin(conflicts[conflicts > 1].index)
    ].drop_duplicates("normalized")
    # Deterministic class cap keeps CPU training practical.
    combined = combined.sample(frac=1, random_state=SETTINGS["training"]["seed"])
    combined = (
        combined.groupby("label")
        .head(SETTINGS["training"]["max_per_class"])
        .reset_index(drop=True)
    )
    templates = combined["text"].map(normalized_template)
    vectors = TfidfVectorizer(max_features=20000, ngram_range=(1, 2)).fit_transform(
        templates
    )
    neighbors = NearestNeighbors(metric="cosine", radius=0.15, n_jobs=2).fit(vectors)
    graph = neighbors.radius_neighbors_graph(vectors, mode="connectivity")
    _, groups = connected_components(graph, directed=False)
    combined["group"] = groups.astype(str)
    combined[["subject", "body", "label", "group", "source"]].to_csv(
        folder / "reviewed.csv", index=False
    )
    audit = {
        "counts": combined.groupby(["source", "label"]).size().to_dict(),
        "groups": int(len(set(groups))),
        "near_duplicate_cosine_threshold": 0.85,
        "limitation": "Source labels retained. Near-duplicate grouping is heuristic; source and age confounding remain.",
    }
    audit["counts"] = {str(key): int(value) for key, value in audit["counts"].items()}
    (folder / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    build()
