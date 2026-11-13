"""Small synthetic diagnostic suite, separate from corpus metrics."""

import json
from email.message import EmailMessage
from ai_email_security.analyzer import analyze
from ai_email_security.config import ROOT, project_path


if __name__ == "__main__":
    cases = json.loads(
        (ROOT / "samples" / "scenarios.json").read_text(encoding="utf-8")
    )
    results = []
    for case in cases:
        message = EmailMessage()
        message["Subject"] = case["subject"]
        message.set_content(case["body"])
        report = analyze(message.as_bytes(), engine="keras")
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected": case["label"],
                "verdict": report["analysis"]["verdict"],
                "score": report["score"],
            }
        )
    folder = project_path("reports")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "scenarios.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, indent=2))
