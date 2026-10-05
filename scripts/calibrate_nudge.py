#!/usr/bin/env python3
"""Replay your own Claude Code messages through each nudge rule and count how often it would fire.

Read-only. Uses the same readers as the report, so messages are labelled and dropped as they are read.
Prints counts only, never message text. Writes nothing.

    python3 scripts/calibrate_nudge.py [--since 60] [--cooldown 45] [--streak 15] [--window 20]
"""
import argparse
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mirror_core.readers import default_dirs, read_claude  # noqa: E402

RESET = ("question", "challenge")
COUNT = ("directive", "approval", "context")


def replay(turns, rule, cooldown, streak_n=15, window=20, ratio=0.9):
    """Fire times for one rule. The cooldown is global, as in the hook; streaks and windows are per session."""
    state = defaultdict(lambda: {"streak": 0, "recent": []})
    last = None
    fired = []
    for t in turns:
        if t.kind not in RESET + COUNT:
            continue
        s = state[t.session]
        active = t.kind in RESET
        s["streak"] = 0 if active else s["streak"] + 1
        s["recent"] = (s["recent"] + [0 if active else 1])[-window:]
        if rule == "streak":
            hit = s["streak"] >= streak_n
        else:
            hit = len(s["recent"]) >= window and sum(s["recent"]) / window >= ratio
        if hit and (last is None or t.ts - last >= timedelta(minutes=cooldown)):
            fired.append(t.ts)
            last = t.ts
            s["streak"], s["recent"] = 0, []
    return fired


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", type=int, default=60)
    p.add_argument("--cooldown", type=int, default=45)
    p.add_argument("--streak", type=int, default=15)
    p.add_argument("--window", type=int, default=20)
    p.add_argument("--claude-dir")
    a = p.parse_args(argv)
    root = Path(a.claude_dir) if a.claude_dir else default_dirs()[0]
    turns, _, _ = read_claude(root, a.since)
    turns.sort(key=lambda t: t.ts)
    counted = [t for t in turns if t.kind in RESET + COUNT]
    if not counted:
        print("No Claude Code messages found.")
        return 1
    days = len({t.ts.date() for t in counted})
    passive = sum(1 for t in counted if t.kind in COUNT)
    print(f"{len(counted)} counted messages over {days} active days; {round(100 * passive / len(counted))}% passive overall.")
    print(f"Cooldown {a.cooldown} min. Firings (per active day):")
    rows = [(f"streak {a.streak}", replay(counted, "streak", a.cooldown, streak_n=a.streak))]
    for r in (0.80, 0.85, 0.90, 0.95, 1.00):
        rows.append((f"ratio >= {r:.2f} over {a.window}", replay(counted, "ratio", a.cooldown, window=a.window, ratio=r)))
    for name, fired in rows:
        print(f"  {name:<22} {len(fired):>4}  ({len(fired) / days:.1f}/day)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
