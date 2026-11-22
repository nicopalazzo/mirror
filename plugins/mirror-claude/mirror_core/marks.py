"""Markers: a date and a few words of your own ("started using Coanda"), in ~/.mirror/marks.jsonl.

The report shows your numbers before and after each one. Markers are your words, like your day notes:
they appear in your own report page and never in the share card. `mirror.py forget` deletes them.
"""
from __future__ import annotations
import json
import os
from datetime import date

from . import store

MAX_LEN = 120


def path():
    return store.home() / "marks.jsonl"


def read():
    """Markers sorted by day (oldest first). Lines that do not parse are skipped."""
    out = []
    try:
        lines = path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            r = json.loads(line)
            out.append({"day": date.fromisoformat(r["day"]).isoformat(), "note": str(r["note"])})
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(out, key=lambda m: m["day"])


def _write(items):
    store.home().mkdir(parents=True, exist_ok=True)
    p = path()
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for m in items:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def add(day, note):
    note = " ".join(str(note).split())
    if not note:
        raise ValueError("Say in a few words what changed, for example: mirror.py mark \"started using a new tool\"")
    if len(note) > MAX_LEN:
        raise ValueError(f"Keep it under {MAX_LEN} characters; this one has {len(note)}.")
    item = {"day": day.isoformat(), "note": note}
    _write(read() + [item])
    return item


def remove(n):
    """Removes the n-th marker as `mark list` numbers them (1 = oldest). Returns it, or None."""
    items = read()
    if not 1 <= n <= len(items):
        return None
    gone = items.pop(n - 1)
    _write(items)
    return gone
