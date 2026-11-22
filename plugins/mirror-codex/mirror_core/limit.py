"""The evening limit: you choose a time to stop working with AI; when you pass it, Mirror holds one message
and shows you the time. Then you decide. Mirror records what you did and shows it back in the report.

Design (22 Nov 2026, with Nicolas: "Mirror doesn't act, it reveals"):
- Off until you set a time (`mirror.py limit set 19:00`, or /mirror:limit in the plugin). Claude cannot set it:
  the plugin skills keep disable-model-invocation.
- Input is only the clock and the prompt the hook receives. No log file is opened and no text is kept:
  ~/.mirror/limit.json holds the time you set, dates, clock times and what you did.
- An evening runs from the limit until 05:00 the next morning, so a message at 00:30 still belongs to the
  evening before. At most one line per evening.
- The line is shown by blocking that one prompt, like the nudge; Enter sends it unchanged. It is a mirror,
  not a lock: nothing stops you, and /mirror:stop only records that you stopped.
- What happened is logged as one word: carried_on (you sent a message after the line), stopped (/mirror:stop),
  left (no message after the line that evening).
- Any error: exit silently. A broken hook must never block or slow the user's prompt.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta, timezone

from . import store

DEFAULTS = {
    "enabled": False,
    "at": None,            # "HH:MM", local time
    "pending": False,
    "pending_day": None,   # the evening (date of its start) the open line belongs to
    "last_offer_day": None,
    "log": [],
}
MAX_LOG = 400
NIGHT_ENDS_HOUR = 5     # an evening runs until 05:00 the next morning
_HHMM = re.compile(r"^([01]?\d|2[0-3])[:hH.]?([0-5]\d)?$")

LINE = ("It's {now}. You set {at} as the time to stop working with AI.\n"
        "Enter: carry on · /mirror:stop: stop here (Mirror only notes it)")


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds") if dt else None


def _path():
    return store.home() / "limit.json"


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


def parse_time(text):
    """'19:00', '19h', '19h30', '7:30' -> 'HH:MM', or None. 24-hour clock only."""
    m = _HHMM.match((text or "").strip())
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2) or '00'}"


def evening_of(local):
    """The evening a local time belongs to: before 05:00 counts for the day before."""
    return (local - timedelta(hours=NIGHT_ENDS_HOUR)).date() if local.hour < NIGHT_ENDS_HOUR else local.date()


def is_past(local, at):
    """True from the limit until 05:00 the next morning."""
    hhmm = local.strftime("%H:%M")
    return hhmm >= at or local.hour < NIGHT_ENDS_HOUR


def _log(st, event, local, **kw):
    st.setdefault("log", []).append(dict({"at": _iso(local), "day": evening_of(local).isoformat(),
                                          "time": local.strftime("%H:%M"), "event": event}, **kw))


def _close(st, answer, local):
    if not st.get("pending"):
        return
    st["pending"] = False
    _log(st, answer, local, evening=st.get("pending_day"))
    st["pending_day"] = None


def on_prompt(prompt, counted, now=None):
    """Called once per user prompt, after the welcome line and before the nudge. Returns the line or None."""
    local = (now or _now()).astimezone()
    st = load()
    if not st["enabled"] or not st.get("at"):
        return None
    text = (prompt or "").lstrip()
    if text.startswith(("/mirror", "$mirror")):
        return None  # the user is answering Mirror; /mirror:stop records itself
    tonight = evening_of(local).isoformat() if is_past(local, st["at"]) else None
    if st.get("pending"):
        if st.get("pending_day") == tonight:
            _close(st, "carried_on", local)
        else:
            _close(st, "left", local)  # no message after the line that evening
    msg = None
    if counted and tonight and st.get("last_offer_day") != tonight:
        st["last_offer_day"] = tonight
        st["pending"], st["pending_day"] = True, tonight
        _log(st, "offer", local, limit=st["at"])
        msg = LINE.format(now=local.strftime("%H:%M"), at=st["at"])
    save(st)
    return msg


def set_time(text, now=None):
    at = parse_time(text)
    if not at:
        return "Give a time on the 24-hour clock, like 19:00 or 19h30."
    local = (now or _now()).astimezone()
    st = load()
    st["enabled"], st["at"] = True, at
    _log(st, "set", local, limit=at)
    save(st)
    return (f"Evening limit set to {at}. The first message you send after {at} is held once, with the time. "
            f"Enter sends it. /mirror:off turns it off.")


def set_enabled(on, now=None):
    """/mirror:on and /mirror:off. On only comes back if a time was set before."""
    local = (now or _now()).astimezone()
    st = load()
    if on and not st.get("at"):
        return
    if not on:
        _close(st, "left", local)
    if st["enabled"] != bool(on):
        st["enabled"] = bool(on)
        _log(st, "on" if on else "off", local)
        save(st)


def stop(now=None):
    local = (now or _now()).astimezone()
    st = load()
    if st.get("pending"):
        _close(st, "stopped", local)
    else:
        _log(st, "stopped", local, evening=evening_of(local).isoformat())
    save(st)
    return f"Noted: you stopped at {local.strftime('%H:%M')}. Mirror will show it in your report."


def evenings(st=None):
    """What happened each evening, for the report: {day: {"offer": "HH:MM", "answer": word, "limit": "HH:MM"}}."""
    st = st or load()
    out = {}
    for e in st.get("log", []):
        if e.get("event") == "offer":
            out[e["day"]] = {"offer": e.get("time"), "limit": e.get("limit"), "answer": None}
        elif e.get("event") in ("carried_on", "stopped", "left"):
            day = e.get("evening") or e.get("day")
            out.setdefault(day, {"offer": None, "limit": st.get("at"), "answer": None})
            if out[day]["answer"] is None:
                out[day]["answer"] = e["event"]
                out[day]["answer_time"] = e.get("time")
            elif e["event"] == "stopped":
                out[day]["stopped_at"] = e.get("time")  # carried on, then stopped later that evening
    return out


def report_data():
    st = load()
    return {"enabled": bool(st.get("enabled")), "at": st.get("at"), "evenings": evenings(st)}


def status():
    st = load()
    if not st.get("at"):
        return "Evening limit: not set. Set one with: mirror.py limit set 19:00"
    ev = evenings(st)
    answers = [v["answer"] for v in ev.values() if v.get("offer")]
    return "\n".join([
        f"Evening limit: {'on' if st['enabled'] else 'off'}; {st['at']}",
        f"Evenings past it: {len(answers)}; carried on {answers.count('carried_on')}, stopped {answers.count('stopped')}, "
        f"no message after it {answers.count('left')}"
        + (f"; carried on, then stopped later: {sum(1 for v in ev.values() if v.get('offer') and v.get('stopped_at'))}"
           if any(v.get("stopped_at") for v in ev.values()) else ""),
    ])
