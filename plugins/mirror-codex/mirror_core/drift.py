"""Session drift: how your messages change over a working stretch and by hour of day. Observation only.

A stretch is your messages in one session with no gap over STRETCH_GAP_MINUTES between them.
For each part of a stretch (minutes in) and each hour of the day, counts are pooled first and shares are
worked out from the pooled counts, never averaged from daily rates. Cells with too few messages are hidden.
No score, no threshold, no advice.
"""
from __future__ import annotations
from collections import defaultdict

from .indexes import ENGAGED, QUICK_SECONDS

STRETCH_GAP_MINUTES = 30
BUCKETS = [(0, 30, "0-30 min"), (30, 60, "30-60 min"), (60, 120, "60-120 min"), (120, None, "120+ min")]
MIN_CELL = 5  # fewer messages (or timed approvals) than this and the cell is hidden


def _bucket(minutes_in):
    for i, (lo, hi, _) in enumerate(BUCKETS):
        if hi is None or minutes_in < hi:
            return i
    return len(BUCKETS) - 1


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    m = n // 2
    return float(xs[m]) if n % 2 else (xs[m - 1] + xs[m]) / 2.0


def _quick_flags(events, quick_seconds):
    """Same rule as indexes._rubber_stamp: an approval right after AI file changes, timed only when the AI turn has a time.
    Returns {id(turn): True/False} for timed approvals after file changes."""
    out = {}
    last_ai, last_timed, run_writes = None, True, 0
    for kind, ts, obj in events:
        if kind == "a":
            last_ai, last_timed = ts, obj.timed
            if obj.cat == "write":
                run_writes += 1
        else:
            if obj.kind == "approval" and run_writes > 0 and last_ai is not None and last_timed:
                out[id(obj)] = (ts - last_ai).total_seconds() < quick_seconds
            run_writes = 0
    return out


def _cell():
    return {"messages": 0, "asked": 0, "lengths": [], "approvals": 0, "quick": 0, "stretches": set()}


def _finish(c, label):
    n, a = c["messages"], c["approvals"]
    shown = n >= MIN_CELL
    return {
        "label": label,
        "messages": n,
        "stretches": len(c["stretches"]),
        "asked": c["asked"],
        "approvals": a,
        "quick": c["quick"],
        # Hidden cells keep their counts (so totals add up) but carry no shares.
        "asked_pct": round(100.0 * c["asked"] / n, 1) if shown else None,
        "median_chars": _median(c["lengths"]) if shown else None,
        "quick_pct": round(100.0 * c["quick"] / a, 1) if a >= MIN_CELL else None,
    }


def drift(turns, actions, quick_seconds=QUICK_SECONDS, dates=None, gap_minutes=STRETCH_GAP_MINUTES):
    """Pooled counts by minutes into a stretch and by hour of day.

    Stretches are found over all the turns given, so a stretch that started before the window still counts
    its minutes from its real start; only messages whose date is in `dates` (when given) are counted.
    """
    by_session = defaultdict(list)
    for t in turns:
        by_session[(t.tool, t.session)].append(("h", t.ts, t))
    for a in actions:
        by_session[(a.tool, a.session)].append(("a", a.ts, a))
    buckets = [_cell() for _ in BUCKETS]
    hours = [_cell() for _ in range(24)]
    stretch_lengths = []
    gap = gap_minutes * 60.0
    sid = 0
    for key, events in by_session.items():
        events.sort(key=lambda e: e[1])
        quick = _quick_flags(events, quick_seconds)
        mine = [obj for kind, _, obj in events if kind == "h" and obj.kind in ENGAGED]
        start = prev = None
        counted = False  # does the current stretch have a message inside the window?
        for t in mine:
            if prev is None or (t.ts - prev).total_seconds() > gap:
                if counted:
                    stretch_lengths.append((prev - start).total_seconds() / 60.0)
                sid += 1
                start, counted = t.ts, False
            prev = t.ts
            if dates is not None and t.ts.date() not in dates:
                continue
            counted = True
            mins = (t.ts - start).total_seconds() / 60.0
            for c in (buckets[_bucket(mins)], hours[t.ts.hour]):
                c["messages"] += 1
                c["stretches"].add(sid)
                c["lengths"].append(t.chars)
                if t.kind in ("question", "challenge"):
                    c["asked"] += 1
                if id(t) in quick:
                    c["approvals"] += 1
                    c["quick"] += 1 if quick[id(t)] else 0
        if counted:
            stretch_lengths.append((prev - start).total_seconds() / 60.0)
    return {
        "gap_minutes": gap_minutes,
        "min_cell": MIN_CELL,
        "stretches": len(stretch_lengths),
        "longest_minutes": round(max(stretch_lengths)) if stretch_lengths else 0,
        "buckets": [_finish(c, lab) for c, (_, _, lab) in zip(buckets, BUCKETS)],
        "hours": [_finish(c, "%02d:00" % h) for h, c in enumerate(hours)],
    }


def first_and_last(d):
    """The first and the latest stretch part with enough messages, for a one-line comparison. None if fewer than two."""
    shown = [b for b in d["buckets"] if b["asked_pct"] is not None]
    if len(shown) < 2:
        return None
    return shown[0], shown[-1]


def in_n(pct):
    """'1 in 5' style wording from a share, for plain sentences."""
    if pct is None:
        return "n/a"
    if pct <= 0:
        return "none"
    if pct >= 25:
        return "%d in 10" % int(pct / 10.0 + 0.5)
    return "1 in %d" % int(100.0 / pct + 0.5)
