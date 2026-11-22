"""Guess first, every week: before the report shows last week's numbers, ask one question in the terminal.

"What share of your messages last week were a question or pushback?" The report then opens with the guess
next to the count, as a gap, and one question to ask yourself. Mirror only shows the gap: it never scores the
guess, never says right or wrong, and keeps no streak.

Design:
- Asked by `report` in a terminal, before the page is built. The page is a static file and cannot write back
  to ~/.mirror without network code, so the question lives where Mirror can keep the answer.
- At most once per calendar week (local time, Monday to Sunday). "Last week" is the previous calendar week.
- Asked only when last week has enough messages to count fairly (MIN_MESSAGES), and never on the same open as
  the first-run quiz: the week the quiz is shown counts as asked.
- Enter skips, silently. A skip stores the week with no numbers, so it is not asked again that week.
- ~/.mirror/guess.json holds a setting and, per week, the guess and the count (two numbers). Never message text.
- On by default; `mirror.py guess off` stops it. `forget` deletes the file with the rest of ~/.mirror.
"""
from __future__ import annotations
import json
from datetime import date, timedelta

from . import store

MIN_MESSAGES = 10  # same floor the report uses before it shows a weekly share
MAX_WEEKS = 104
QUESTION = "What share of your messages last week were a question or pushback?"
ASK = "Which messages from last week were you thinking of when you guessed?"


def _path():
    return store.home() / "guess.json"


def load():
    st = {"enabled": True, "weeks": []}
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            st["enabled"] = bool(raw.get("enabled", True))
            st["weeks"] = [w for w in raw.get("weeks", []) if isinstance(w, dict) and isinstance(w.get("week"), str)]
    except (OSError, ValueError):
        pass
    return st


def save(st):
    store.home().mkdir(parents=True, exist_ok=True)
    st["weeks"] = st.get("weeks", [])[-MAX_WEEKS:]
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(_path())


def last_week(today=None):
    """(monday, sunday, key) of the calendar week before `today`. key is the ISO week, e.g. "2026-W46"."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday() + 7)
    y, w, _ = monday.isocalendar()
    return monday, monday + timedelta(days=6), f"{y}-W{w:02d}"


def count(all_days, today=None):
    """Last week's share of messages that were a question or pushback, pooled over the week.
    Returns {"week", "start", "end", "messages", "share"}; share is None below MIN_MESSAGES."""
    mon, sun, key = last_week(today)
    days = [s for d, s in all_days.items() if mon <= d <= sun]
    eng = sum(s["_counts"]["engaged"] for s in days)
    hits = sum(s["_counts"]["challenge"] + s["_counts"]["question"] for s in days)
    share = round(100 * hits / eng, 1) if eng >= MIN_MESSAGES else None
    return {"week": key, "start": mon.isoformat(), "end": sun.isoformat(), "messages": eng, "share": share}


def _entry(st, key):
    return next((w for w in st["weeks"] if w["week"] == key), None)


def due(all_days, today=None):
    """The count to ask about, or None (off, already asked this week, or too few messages last week)."""
    st = load()
    if not st["enabled"]:
        return None
    c = count(all_days, today)
    if c["share"] is None or _entry(st, c["week"]):
        return None
    return c


def parse(text):
    """A share from 0 to 100, with or without %; None if it is not one."""
    t = str(text).strip().rstrip("%").strip().replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return round(v, 1) if 0 <= v <= 100 else None


def record(c, guess):
    """Store one week: the guess and the count, or the week alone when skipped (guess None)."""
    st = load()
    st["weeks"] = [w for w in st["weeks"] if w["week"] != c["week"]]
    row = {"week": c["week"]}
    if guess is not None:
        row.update(guess=guess, count=c["share"])
    st["weeks"].append(row)
    st["weeks"].sort(key=lambda w: w["week"])
    save(st)


def mark_asked(all_days, today=None):
    """The first-run quiz is on this open: count this week as asked, so the two never meet."""
    c = count(all_days, today)
    st = load()
    if st["enabled"] and not _entry(st, c["week"]):
        record(c, None)


def ask(c, read=None, say=print):
    """Ask once in the terminal. Enter (or anything that is not a share, twice) skips without a word."""
    read = read or input
    say("")
    say("Before you look: " + QUESTION)
    for attempt in range(2):
        try:
            ans = read("Your guess, 0 to 100 (Enter to skip): ")
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if not ans.strip():
            break
        v = parse(ans)
        if v is not None:
            record(c, v)
            say("Kept. The report shows your guess next to the count.")
            return v
        if attempt == 0:
            say("Please type a number from 0 to 100, or press Enter to skip.")
    record(c, None)
    return None


def for_report(just=None):
    """What the page shows: this open's guess (if one was just made) and the past weeks with a guess."""
    st = load()
    hist = [{"week": w["week"], "guess": w["guess"], "count": w["count"]} for w in st["weeks"]
            if isinstance(w.get("guess"), (int, float)) and isinstance(w.get("count"), (int, float))]
    now = None
    if just and just.get("guess") is not None:
        now = dict(just, ask=ASK)
    return {"now": now, "history": hist[-12:]}


def set_enabled(on):
    st = load()
    st["enabled"] = bool(on)
    save(st)


def status():
    st = load()
    n = len([w for w in st["weeks"] if w.get("guess") is not None])
    return f"Weekly guess: {'on' if st['enabled'] else 'off'}; weeks with a guess kept: {n}."
