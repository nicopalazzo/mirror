"""Numbers-only ledger: one line per day in ~/.mirror/days.jsonl, so your history outlives the tools' own log cleanup.

Each line holds the per-day counts the report already shows (no message text, no project names or hashes,
no session ids), plus the labelling-rules version and the quick-approval line they were counted with.
Days still in the logs are recomputed on every run; days the logs no longer hold come from here.
`mirror.py forget` deletes it with the rest of ~/.mirror.
"""
from __future__ import annotations
import json
import os
from datetime import date

from . import store
from .classify import RULES_VERSION
from .indexes import day_stats

# Only these keys of a day's numbers are written. A new field in day_stats stays out until it is added here
# on purpose (and THREAT-MODEL.md says what it is).
FIELDS = ("prompts", "kinds", "tools", "sessions", "projects", "first", "last", "active_minutes", "ai_actions",
          "ai_replies", "cats", "hours_prompts", "hours_actions", "hours_approvals", "hours_quick", "idx", "_counts")
HOUR_FIELDS = ("hours_prompts", "hours_actions", "hours_approvals", "hours_quick")


def path():
    return store.home() / "days.jsonl"


def enabled():
    """On unless you ran `mirror.py ledger off` (stored as "ledger": "off" in config.json)."""
    return store.load_config().get("ledger") != "off"


def set_enabled(on):
    cfg = store.load_config()
    if on:
        cfg.pop("ledger", None)
    else:
        cfg["ledger"] = "off"
    store.save_config(cfg)


def delete():
    """Deletes days.jsonl only (`mirror.py ledger forget`). Returns True if there was one."""
    try:
        path().unlink()
        return True
    except OSError:
        return False


def _clean(stats):
    return {k: stats[k] for k in FIELDS if k in stats}


def _events(s):
    """Everything Mirror counted that day: your messages of every kind plus every AI action."""
    return sum((s.get("kinds") or {}).values()) + sum((s.get("cats") or {}).values())


def _restore(stats):
    """A day read back from the file, in the same shape day_stats returns (hour keys as numbers, no missing keys)."""
    out = day_stats([], [])
    for k in FIELDS:
        if k not in stats:
            continue
        v = stats[k]
        if k in HOUR_FIELDS and isinstance(v, dict):
            v = {int(h): n for h, n in v.items()}
        if isinstance(out.get(k), dict) and isinstance(v, dict) and k in ("idx", "_counts"):
            v = dict(out[k], **v)
        out[k] = v
    return out


def read():
    """{date: {"rules": int, "quick_seconds": int, "stats": {...}}}. Lines that do not parse are skipped."""
    rows = {}
    try:
        lines = path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            r = json.loads(line)
            d = date.fromisoformat(r["date"])
            s = r["stats"]
            if not isinstance(s, dict) or not all(isinstance(s.get(k), dict) for k in ("kinds", "cats", "idx", "_counts")):
                continue
            rows[d] = {"rules": r.get("rules"), "quick_seconds": r.get("quick_seconds"), "stats": _restore(s)}
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
    return rows


def merge(log_days, quick_seconds, rows=None):
    """Logs win for every day they still hold, unless the ledger already counted more for that day
    (the tool has since deleted some of that day's sessions). Returns (days, rows_to_write, info)."""
    rows = read() if rows is None else rows
    days = dict(log_days)
    out = {d: {"rules": RULES_VERSION, "quick_seconds": quick_seconds, "stats": s} for d, s in log_days.items()}
    kept = []
    for d, r in rows.items():
        if d not in days or _events(r["stats"]) > _events(days[d]):
            days[d] = r["stats"]
            out[d] = r
            kept.append(d)
    other = [d for d in kept if rows[d]["rules"] != RULES_VERSION or rows[d]["quick_seconds"] != quick_seconds]
    info = {"days": len(kept), "first": min(kept).isoformat() if kept else None,
            "other_rules": len(other), "rules": RULES_VERSION}
    return dict(sorted(days.items())), dict(sorted(out.items())), info


def write(rows):
    """Rewrites the whole file through a temporary file, so a crash never leaves half a ledger."""
    store.home().mkdir(parents=True, exist_ok=True)
    p = path()
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for d, r in rows.items():
            fh.write(json.dumps({"date": d.isoformat(), "rules": r["rules"], "quick_seconds": r["quick_seconds"],
                                 "stats": _clean(r["stats"])}, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def update(log_days, quick_seconds):
    """Merge, then save. Returns (days, info). A failed write never stops the run: you still get your numbers.
    When the ledger is off, it is neither read nor written: you get the days the logs still hold."""
    if not enabled():
        return dict(log_days), {"days": 0, "first": None, "other_rules": 0, "rules": RULES_VERSION, "created": False, "off": True}
    existed = path().exists()
    days, rows, info = merge(log_days, quick_seconds)
    info["created"] = False
    if rows:
        try:
            write(rows)
            info["created"] = not existed
        except OSError:
            info["write_failed"] = True
    return days, info
