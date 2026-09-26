#!/usr/bin/env python3
"""Copy the shared engine into each platform plugin. Run after changing mirror.py or mirror_core/."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "plugins" / "mirror-claude"]


def build():
    for t in TARGETS:
        shutil.rmtree(t / "mirror_core", ignore_errors=True)
        shutil.copytree(ROOT / "mirror_core", t / "mirror_core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "mirror.py", t / "mirror.py")
        print("built", t.relative_to(ROOT))


if __name__ == "__main__":
    build()
