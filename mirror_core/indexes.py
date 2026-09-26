"""Turns turns/actions into per-day numbers and four plain indexes. Observation only: no scores, no verdicts."""
from __future__ import annotations
from collections import defaultdict, Counter
from datetime import timedelta

ENGAGED = ("directive", "question", "approval", "challenge", "context")
QUICK_SECONDS = 15
IDLE_GAP = 300  # seconds; gaps longer than this are not counted as active time


def _pct(n, d):
    return None if not d else round(100.0 * n / d, 1)


def _rubber_stamp(turns, actions, quick_seconds):
    """Approvals that came within quick_seconds of an AI turn that changed files."""
    by_session = defaultdict(list)
    for t in turns:
        by_session[(t.tool, t.session)].append(("h", t.ts, t))
    for a in actions:
        by_session[(a.tool, a.session)].append(("a", a.ts, a))
    quick = total = 0
    longest = 0
    writes_total = 0
    for events in by_session.values():
        events.sort(key=lambda e: e[1])
        last_ai = None
        run_writes = 0
        for kind, ts, obj in events:
            if kind == "a":
                last_ai = ts
                if obj.cat == "write":
                    run_writes += 1
                    writes_total += 1
                    longest = max(longest, run_writes)
            else:
                if obj.kind == "approval" and run_writes > 0 and last_ai is not None:
                    total += 1
                    if (ts - last_ai).total_seconds() < quick_seconds:
                        quick += 1
                run_writes = 0
    return quick, total, longest


def _active_minutes(stamps):
    stamps = sorted(stamps)
    secs = 0.0
    for a, b in zip(stamps, stamps[1:]):
        g = (b - a).total_seconds()
        if g <= IDLE_GAP:
            secs += g
    return round(secs / 60.0)


def day_stats(turns, actions, quick_seconds=QUICK_SECONDS):
    """turns/actions already filtered to one local day."""
    kinds = Counter(t.kind for t in turns)
    engaged = sum(kinds[k] for k in ENGAGED)
    cats = Counter(a.cat for a in actions)
    tools = sorted({t.tool for t in turns} | {a.tool for a in actions})
    sessions = {(t.tool, t.session) for t in turns} | {(a.tool, a.session) for a in actions}
    projects = {(t.tool, t.project) for t in turns} | {(a.tool, a.project) for a in actions}
    stamps = [t.ts for t in turns] + [a.ts for a in actions]
    quick, appr_after_writes, longest = _rubber_stamp(turns, actions, quick_seconds)
    non_reply = sum(v for k, v in cats.items() if k != "reply")
    hours_h = Counter(t.ts.hour for t in turns if t.kind != "meta")
    hours_a = Counter(a.ts.hour for a in actions)
    return {
        "prompts": engaged,
        "kinds": dict(kinds),
        "tools": tools,
        "sessions": len(sessions),
        "projects": len(projects),
        "first": min(stamps).strftime("%H:%M") if stamps else None,
        "last": max(stamps).strftime("%H:%M") if stamps else None,
        "active_minutes": _active_minutes(stamps) if stamps else 0,
        "ai_actions": non_reply,
        "ai_replies": cats.get("reply", 0),
        "cats": dict(cats),
        "hours_prompts": dict(hours_h),
        "hours_actions": dict(hours_a),
        "idx": {
            "pushback_pct": _pct(kinds["challenge"], engaged),
            "question_pct": _pct(kinds["question"], engaged),
            "approval_pct": _pct(kinds["approval"], engaged),
            "quick_approvals": quick,
            "approvals_after_writes": appr_after_writes,
            "actions_per_prompt": None if not engaged else round(non_reply / engaged, 1),
            "writes": cats.get("write", 0),
            "longest_write_run": longest,
        },
        "_counts": {"engaged": engaged, "challenge": kinds["challenge"], "question": kinds["question"], "approval": kinds["approval"]},
    }


def by_day(turns, actions, quick_seconds=QUICK_SECONDS):
    days = defaultdict(lambda: ([], []))
    for t in turns:
        days[t.ts.date()][0].append(t)
    for a in actions:
        days[a.ts.date()][1].append(a)
    return {d: day_stats(tt, aa, quick_seconds) for d, (tt, aa) in sorted(days.items())}


def pooled(day_list):
    """Pool counts over several days (not an average of rates)."""
    eng = sum(s["_counts"]["engaged"] for s in day_list)
    ch = sum(s["_counts"]["challenge"] for s in day_list)
    q = sum(s["_counts"]["question"] for s in day_list)
    ap = sum(s["_counts"]["approval"] for s in day_list)
    quick = sum(s["idx"]["quick_approvals"] for s in day_list)
    aaw = sum(s["idx"]["approvals_after_writes"] for s in day_list)
    acts = sum(s["ai_actions"] for s in day_list)
    return {
        "days": len(day_list),
        "prompts": eng,
        "pushback_pct": _pct(ch, eng),
        "question_pct": _pct(q, eng),
        "approval_pct": _pct(ap, eng),
        "quick_approvals": quick,
        "approvals_after_writes": aaw,
        "actions_per_prompt": None if not eng else round(acts / eng, 1),
        "active_minutes": sum(s["active_minutes"] for s in day_list),
    }


def baseline(all_days, day, window=7):
    """Your own previous days before `day` (up to `window` active days). Never other people."""
    prior = [s for d, s in all_days.items() if d < day and (day - d) <= timedelta(days=window * 2)]
    prior = prior[-window:]
    return pooled(prior) if prior else None
