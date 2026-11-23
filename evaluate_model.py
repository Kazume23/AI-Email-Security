import hashlib
import json
import pandas as pd
from ai_email_security.config import project_path
from ai_email_security.keras_client import load_bundle
from ai_email_security.evaluation import evaluate_scores
from train_model import dataset


if __name__ == "__main__":
    model, metadata = load_bundle()
    test_path = project_path("data") / "test.jsonl"
    if (
        hashlib.sha256(test_path.read_bytes()).hexdigest()
        != metadata["manifest"]["splits"]["test"]["sha256"]
    ):
        raise ValueError("Test split does not match model manifest")
    frame = pd.read_json(test_path, lines=True)
    scores = model.predict(
        dataset(frame, metadata["settings"]["batch_size"]), verbose=0
    ).ravel()
    report = {
        "model_id": metadata["model_id"],
        "dataset_id": metadata["dataset_id"],
        "thresholds": metadata["thresholds"],
        **evaluate_scores(frame["label"], scores, metadata["thresholds"]),
    }
    folder = project_path("reports")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{metadata['model_id']}-test.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
