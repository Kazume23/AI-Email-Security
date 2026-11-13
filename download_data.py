"""Download versioned public research files; never open email links."""

import hashlib
import json
import urllib.request
import pandas as pd
from ai_email_security.config import SETTINGS, project_path


def download():
    folder = project_path("data") / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {**SETTINGS["dataset"], "checksums": {}}
    for name in SETTINGS["dataset"]["files"]:
        target = folder / name
        if not target.exists():
            temporary = target.with_suffix(".part")
            urllib.request.urlretrieve(
                SETTINGS["dataset"]["url"] + name + "?download=1", temporary
            )
            temporary.replace(target)
        with target.open("rb") as stream:
            manifest["checksums"][name] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
        frame = pd.read_csv(target)
        print(name, frame.shape, frame.columns.tolist())
        print(frame["label"].value_counts().to_dict())
    (folder / "source.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    download()
