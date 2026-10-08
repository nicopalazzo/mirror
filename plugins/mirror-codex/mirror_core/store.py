"""Everything Mirror writes lives in one folder: ~/.mirror (override with MIRROR_HOME). `forget` deletes it."""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("MIRROR_HOME") or (Path.home() / ".mirror"))


def reports_dir() -> Path:
    """Where reports go. A normal, visible folder in your home directory (not Documents or Desktop, which
    iCloud and OneDrive often sync to the cloud). Override with MIRROR_REPORTS. When MIRROR_HOME is set
    (tests), reports stay inside it."""
    if os.environ.get("MIRROR_REPORTS"):
        return Path(os.environ["MIRROR_REPORTS"])
    if os.environ.get("MIRROR_HOME"):
        return home() / "reports"
    return Path.home() / "Mirror"


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


def quiz_pending() -> bool:
    """True only for a new install whose first report has not been built yet. Stores a word, never your guesses."""
    return load_config().get("quiz") == "pending"


def set_quiz(state):
    cfg = load_config()
    cfg["quiz"] = state
    save_config(cfg)


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
    """Deletes ~/.mirror and Mirror's own report files. Never removes other files in the reports folder."""
    removed = False
    r = reports_dir()
    if r.is_dir() and home() not in r.parents:
        for f in r.glob("mirror-*.html"):
            f.unlink()
            removed = True
        try:
            r.rmdir()  # only succeeds if it is now empty
        except OSError:
            pass
    h = home()
    if h.exists():
        shutil.rmtree(h)
        removed = True
    return removed
