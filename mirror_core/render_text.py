"""Terminal output. ASCII only so it prints the same on macOS and Windows consoles."""
from __future__ import annotations
from .indexes import baseline, pooled
from .explain import INDEXES, DISCLAIMER

KIND_LABEL = {
    "directive": "asked the AI to do something",
    "question": "asked a question",
    "approval": "agreed / told it to go on",
    "challenge": "pushed back or corrected",
    "context": "shared context or an opinion",
}


def _bar(n, total, width=24):
    if not total:
        return ""
    return "#" * max(1, round(width * n / total)) if n else ""


def _fmt(v, suffix=""):
    return "n/a" if v is None else f"{v}{suffix}"


def _usual(cur, base, key, suffix="%"):
    if base is None or base.get(key) is None or cur is None:
        return ""
    b = base[key]
    if abs(cur - b) < 0.5:
        return f"  (about your usual {b}{suffix})"
    return f"  ({'higher' if cur > b else 'lower'} than your usual {b}{suffix})"


def day_text(day, stats, all_days, tools_missing=()):
    s = stats
    base = baseline(all_days, day)
    lines = []
    lines.append(f"Mirror - {day.strftime('%A %d %B %Y')}")
    lines.append("=" * 46)
    if not s["prompts"] and not s["ai_actions"]:
        lines.append("No AI activity found for this day.")
        return "\n".join(lines)
    lines.append(f"Tools: {', '.join(s['tools']) or '-'}    Sessions: {s['sessions']}    Projects: {s['projects']}")
    lines.append(f"Active: about {s['active_minutes']} min, between {s['first']} and {s['last']}")
    lines.append(f"You sent {s['prompts']} prompts; the AI took {s['ai_actions']} actions.")
    lines.append("")
    lines.append("What you did")
    for k, label in KIND_LABEL.items():
        n = s["kinds"].get(k, 0)
        if n:
            lines.append(f"  {label:<32} {n:>3}  {_bar(n, s['prompts'])}")
    pasted = s["kinds"].get("pasted", 0)
    if pasted:
        lines.append(f"  {'pasted long text':<32} {pasted:>3}  (not counted above)")
    lines.append("")
    lines.append("Four numbers, as questions (not scores)")
    i = s["idx"]
    lines.append("")
    lines.append(f"1. Challenge rate: pushback {_fmt(i['pushback_pct'], '%')}, questions {_fmt(i['question_pct'], '%')}"
                 + _usual(i["pushback_pct"], base, "pushback_pct"))
    lines.append(f"   Ask yourself: {INDEXES['challenge']['ask']}")
    if i["approvals_after_writes"]:
        lines.append(f"2. Quick approvals: {i['quick_approvals']} of {i['approvals_after_writes']} approvals after file changes came within 15 s")
    else:
        lines.append(f"2. Approvals: {_fmt(i['approval_pct'], '%')} of prompts; none directly after file changes today")
    lines.append(f"   Ask yourself: {INDEXES['approval']['ask']}")
    lines.append(f"3. Delegation depth: {_fmt(i['actions_per_prompt'])} AI actions per prompt; longest run of file changes without a message from you: {i['longest_write_run']}"
                 + _usual(i["actions_per_prompt"], base, "actions_per_prompt", ""))
    lines.append(f"   Ask yourself: {INDEXES['delegation']['ask']}")
    lines.append(f"4. Focus: {s['sessions']} sessions, {s['projects']} projects, {len(s['tools'])} tools, {s['active_minutes']} active minutes")
    lines.append(f"   Ask yourself: {INDEXES['focus']['ask']}")
    for t in tools_missing:
        lines.append("")
        lines.append(f"Note: {t}")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("Run `mirror explain challenge|approval|delegation|focus` for what each number can and cannot tell you.")
    return "\n".join(lines)


def week_text(all_days, end_day, days=7):
    from datetime import timedelta
    window = [(d, s) for d, s in all_days.items() if 0 <= (end_day - d).days < days]
    prev = [(d, s) for d, s in all_days.items() if days <= (end_day - d).days < 2 * days]
    lines = [f"Mirror - week ending {end_day.strftime('%A %d %B %Y')}", "=" * 46]
    if not window:
        lines.append("No AI activity found in this window.")
        return "\n".join(lines)
    lines.append(f"{'day':<12}{'prompts':>8}{'active min':>12}{'pushback':>10}{'quick appr.':>13}{'actions/prompt':>16}")
    for d, s in window:
        i = s["idx"]
        qa = f"{i['quick_approvals']}/{i['approvals_after_writes']}" if i["approvals_after_writes"] else "-"
        lines.append(f"{d.strftime('%a %d %b'):<12}{s['prompts']:>8}{s['active_minutes']:>12}{_fmt(i['pushback_pct'], '%'):>10}{qa:>13}{_fmt(i['actions_per_prompt']):>16}")
    cur = pooled([s for _, s in window])
    lines.append("")
    lines.append(f"This window: {cur['prompts']} prompts over {cur['days']} active days; pushback {_fmt(cur['pushback_pct'], '%')}, questions {_fmt(cur['question_pct'], '%')}, approvals {_fmt(cur['approval_pct'], '%')}.")
    if prev:
        p = pooled([s for _, s in prev])
        lines.append(f"Before that ({p['days']} active days): pushback {_fmt(p['pushback_pct'], '%')}, questions {_fmt(p['question_pct'], '%')}, approvals {_fmt(p['approval_pct'], '%')}.")
        lines.append("Compared with your own earlier days only, never with other people.")
    else:
        lines.append("No earlier days to compare with yet.")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def explain_text(key):
    e = INDEXES[key]
    return "\n".join([
        e["title"], "-" * len(e["title"]),
        "What it measures: " + e["measures"],
        "What it cannot tell you: " + e["cannot"],
        "A question to ask yourself: " + e["ask"],
        "A practice you could try (untested, your call): " + e["practice"],
    ])
