"""Configuration shared by inference and training (Python 3.11+)."""

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("EMAIL_SECURITY_CONFIG", ROOT / "config.toml"))
with CONFIG_PATH.open("rb") as source:
    SETTINGS = tomllib.load(source)


def project_path(key):
    path = Path(SETTINGS["paths"][key])
    return path if path.is_absolute() else ROOT / path
