"""Everything Mirror writes lives in one folder: ~/.mirror (override with MIRROR_HOME). `forget` deletes it."""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("MIRROR_HOME") or (Path.home() / ".mirror"))


def _cfg_path():
    return home() / "config.json"


def load_config():
    try:
        return json.loads(_cfg_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    home().mkdir(parents=True, exist_ok=True)
    _cfg_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def add_feedback(entry):
    home().mkdir(parents=True, exist_ok=True)
    with open(home() / "feedback.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_feedback():
    p = home() / "feedback.jsonl"
    out = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def forget():
    h = home()
    if h.exists():
        shutil.rmtree(h)
        return True
    return False
