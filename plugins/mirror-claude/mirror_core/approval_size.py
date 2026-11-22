"""Observation only: no scores, no thresholds, no advice."""
from __future__ import annotations
from collections import defaultdict
from statistics import median

from .indexes import QUICK_SECONDS


BUCKETS = [("under 20", 0, 20), ("20 to 200", 20, 201), ("over 200", 201, None)]
MIN_RUNS = 5


def size_runs(turns, actions, quick_seconds=QUICK_SECONDS):
    grouped = defaultdict(list)
    for turn in turns:
        grouped[(turn.tool, turn.session)].append((turn.ts, 1, turn))
    for action in actions:
        grouped[(action.tool, action.session)].append((action.ts, 0, action))
    runs = []
    for events in grouped.values():
        events.sort(key=lambda event: (event[0], event[1]))
        pending = []
        for ts, is_turn, item in events:
            if not is_turn:
                pending.append(item)
                continue
            writes = [action for action in pending if action.cat == "write"]
            if writes and all(action.timed for action in pending):
                last = pending[-1]
                reply_s = (item.ts - last.ts).total_seconds()
                runs.append({"lines": sum(action.lines for action in writes), "writes": len(writes),
                             "run_s": (last.ts - writes[0].ts).total_seconds(), "reply_s": reply_s,
                             "quick": item.kind == "approval" and reply_s < quick_seconds, "date": item.ts.date()})
            pending = []
    return runs


def buckets(runs):
    out = []
    for label, lo, hi in BUCKETS:
        selected = [run for run in runs if run["lines"] >= lo and (hi is None or run["lines"] < hi)]
        row = {"label": label, "runs": len(selected), "shown": len(selected) >= MIN_RUNS}
        if row["shown"]:
            row.update(reply_median_s=round(median(run["reply_s"] for run in selected)),
                       run_median_s=round(median(run["run_s"] for run in selected)),
                       quick_pct=round(100 * sum(run["quick"] for run in selected) / len(selected), 1))
        out.append(row)
    return out


def summary(runs):
    return {"runs": len(runs), "days": len({run["date"] for run in runs}), "buckets": buckets(runs)}
