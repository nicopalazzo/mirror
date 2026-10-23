"""The welcome-back line: when you return to your AI tool after a break, hold the first message once and
ask "Take a quick look in the Mirror?". Then you work.

Design (research/MIRROR-WELCOME-BACK-DRAFT.md, 9 Oct 2026):
- Input is only the clock and the prompt the tool hands to the hook. No log file is opened and no text is
  kept: ~/.mirror/welcome.json holds times, counts and settings only.
- Off until the user opts in (/mirror:on turns on the nudge and the welcome together).
- "start-of-week" (default): the first prompt in a new calendar week (local time, Monday 00:00), or after a gap
  of `gap_days` or more, at most once a week. "start-of-day": the first prompt after a gap of 8 hours or more,
  at most once a day.
- The line is shown by blocking that one prompt, like the nudge; Enter sends the original message unchanged.
  Claude never sees the line. The report is never opened for the user: they type /mirror:report.
- The answer is logged as a count: opened (a report was built), skipped (the user carried on), snoozed, off.
  Three skipped offers in a row pause the welcome for 30 days, said once. Skips are never shown as a score.
- Hold-back (`holdback` > 0): that share of offers is silently held back, so reports opened after an offer
  can be compared with weeks without one. Off (0.0) by default.
- Any error: exit silently. A broken hook must never block or slow the user's prompt.
"""
from __future__ import annotations
import json
import random
from datetime import datetime, timedelta, timezone

from . import store

DEFAULTS = {
    "enabled": False,
    "when": "start-of-week",
    "gap_days": 3,
    "holdback": 0.0,
    "snooze_until": None,
    "last_seen": None,
    "last_offer": None,
    "pending": False,
    "pending_arm": None,
    "skipped_in_row": 0,
    "log": [],
}
WHEN = ("start-of-week", "start-of-day")
DAY_GAP_HOURS = 8
PAUSE_DAYS = 30
MAX_LOG = 200

LINE = "Welcome back. Take a quick look in the Mirror? Last week is ready.\n/mirror:report: open it · Enter: carry on"
PAUSE_LINE = ("No look at the last 3 welcomes, so Mirror will not offer one for a month.\n"
              "/mirror:on: resume · /mirror:off: turn off")

_rand = random.random  # replaced in tests


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds") if dt else None


def _parse(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def _path():
    return store.home() / "welcome.json"


def load():
    st = dict(DEFAULTS)
    try:
        st.update(json.loads(_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return st


def save(st):
    store.home().mkdir(parents=True, exist_ok=True)
    st["log"] = st.get("log", [])[-MAX_LOG:]
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(_path())


def _log(st, event, now=None, **kw):
    st.setdefault("log", []).append(dict({"at": _iso(now or _now()), "event": event}, **kw))


def _week(dt):
    """Calendar week in local time (Monday to Sunday), as (iso year, iso week)."""
    y, w, _ = dt.astimezone().isocalendar()
    return y, w


def _close_pending(st, response, now):
    if not st.get("pending"):
        return
    arm = st.get("pending_arm") or "shown"
    st["pending"], st["pending_arm"] = False, None
    _log(st, "response", now, response=response, arm=arm)
    if arm != "shown":
        return  # the user saw nothing, so nothing was skipped
    st["skipped_in_row"] = st.get("skipped_in_row", 0) + 1 if response == "skipped" else 0


def _due(st, last_seen, now):
    if last_seen is None or now <= last_seen:
        return False  # first prompt Mirror has seen, or the clock went back: nothing to come back from
    gap = now - last_seen
    if st.get("when") == "start-of-day":
        last = _parse(st.get("last_offer"))
        return gap >= timedelta(hours=DAY_GAP_HOURS) and (last is None or last.astimezone().date() != now.astimezone().date())
    new_week = _week(now) != _week(last_seen)
    long_gap = gap >= timedelta(days=int(st.get("gap_days") or 3))
    last = _parse(st.get("last_offer"))
    once_a_week = last is None or _week(last) != _week(now)
    return (new_week or long_gap) and once_a_week


def on_prompt(prompt, counted, now=None):
    """Called once per user prompt, before the nudge. `counted` is False for commands and pasted text, which
    are never held. Returns the one line to show the user, or None."""
    now = now or _now()
    st = load()
    if not st["enabled"]:
        return None
    text = (prompt or "").lstrip()
    if text.startswith(("/mirror", "$mirror")):
        # The user is answering Mirror; /mirror:report is also recorded when the report is built.
        if st.get("pending") and text.split()[0].endswith(":report"):
            _close_pending(st, "opened", now)
        st["last_seen"] = _iso(now)
        save(st)
        return None
    if st.get("pending"):
        _close_pending(st, "skipped", now)  # the held message was sent as it was
    last_seen = _parse(st.get("last_seen"))
    snooze = _parse(st.get("snooze_until"))
    msg = None
    if counted and (snooze is None or now >= snooze) and _due(st, last_seen, now):
        st["last_offer"] = _iso(now)
        if st.get("skipped_in_row", 0) >= 3:
            st["snooze_until"] = _iso(now + timedelta(days=PAUSE_DAYS))
            st["skipped_in_row"] = 0
            _log(st, "pause", now)
            msg = PAUSE_LINE
        else:
            st["pending"] = True
            if _rand() < float(st.get("holdback") or 0.0):
                st["pending_arm"] = "held"
                _log(st, "withheld", now)
            else:
                st["pending_arm"] = "shown"
                _log(st, "offer", now)
                msg = LINE
    st["last_seen"] = _iso(now)
    save(st)
    return msg


def note_report(now=None):
    """A report was built: if an offer is waiting, that is its answer."""
    now = now or _now()
    st = load()
    if st.get("pending"):
        _close_pending(st, "opened", now)
        save(st)


def set_enabled(on, now=None):
    now = now or _now()
    st = load()
    if on:
        st["enabled"], st["snooze_until"], st["skipped_in_row"] = True, None, 0
        st["last_seen"] = st.get("last_seen") or _iso(now)
        _log(st, "on", now)
    else:
        _close_pending(st, "off", now)
        st["enabled"] = False
        _log(st, "off", now)
    save(st)


def snooze(until, now=None):
    now = now or _now()
    st = load()
    if st["enabled"]:
        _close_pending(st, "snoozed", now)
        st["snooze_until"] = _iso(until)
        save(st)


SETTINGS = {
    "when": (str, None, None, "start-of-week or start-of-day"),
    "gap-days": (int, 2, 14, "days away that count as a return"),
    "holdback": (float, 0.0, 0.9, "share of offers held back as a comparison"),
}
_KEYS = {"gap-days": "gap_days"}


def configure(name, value):
    if name not in SETTINGS:
        return f"Unknown setting: {name}. Settings: {', '.join(SETTINGS)}."
    typ, lo, hi, what = SETTINGS[name]
    try:
        v = typ(value)
        if typ is str:
            if v not in WHEN:
                raise ValueError
        elif not lo <= v <= hi:
            raise ValueError
    except (TypeError, ValueError):
        rng = " or ".join(WHEN) if typ is str else f"{lo} to {hi}"
        return f"{name} must be {rng} ({what})."
    st = load()
    st[_KEYS.get(name, name)] = v
    _log(st, "config", setting=name, value=v)
    save(st)
    return f"{name} set to {v}."


def status():
    st = load()
    resp = [e.get("response") for e in st["log"] if e["event"] == "response" and (e.get("arm") or "shown") == "shown"]
    offers = len([e for e in st["log"] if e["event"] == "offer"])
    held = [e.get("response") for e in st["log"] if e["event"] == "response" and e.get("arm") == "held"]
    lines = [
        f"Welcome: {'on' if st['enabled'] else 'off'}; when: {st['when']}"
        + (f" (a return is {st['gap_days']} days away)" if st["when"] == "start-of-week" else ""),
        f"Snoozed until: {st['snooze_until'] or '-'}",
        f"Offers shown: {offers}; opened the report {resp.count('opened')}, carried on {resp.count('skipped')}, "
        f"snoozed {resp.count('snoozed')}, off {resp.count('off')}",
    ]
    if held or st.get("holdback"):
        lines.append(f"Hold-back test ({round(100 * float(st.get('holdback') or 0))}% held back): "
                     f"{len(held)} moments held back, report opened after {held.count('opened')} "
                     f"(small samples: a direction, not a result)")
    return "\n".join(lines)
