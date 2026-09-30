"""The nudge: sense a streak, decide, show one line to the user, respect the answer.

Design (see THREAT-MODEL.md and the JITAI framework, Nahum-Shani et al. 2018):
- Input is only the prompt the tool hands to the hook. No log file is opened.
- The prompt is labelled and dropped at once; state keeps counts and times only.
- Off until the user opts in (/mirror:on). One intro line on first sight.
- Fires when the streak of messages without a question or pushback reaches the threshold,
  outside the cooldown, and not snoozed. Then the streak resets.
- The first counted message after a nudge is its answer: a question or pushback is "acted",
  any other non-approval is "edited" (the user changed the message), and a plain approval is
  "sent_anyway", the only answer that counts as ignored (29 Sep 2026: before this, pushing back
  after a nudge was logged as ignored). A nudge with no message after it counts as ignored too.
  Each ignored nudge doubles the cooldown (max 8x).
  Three ignored in a row pauses Mirror for a day and says so once ("provide nothing").
- A nudge blocks that one prompt and shows its line where the user is typing; the prompt stays in
  the input box, so Enter sends it. Claude Code does not display systemMessage from this hook
  (tested 26 Sep 2026, v2.1.283, Desktop app and CLI), so blocking is the only direct channel.
- Any error: exit silently. A broken hook must never block or slow the user's prompt.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone

from . import store
from .classify import classify

DEFAULTS = {
    "enabled": False,
    "introduced": False,
    "threshold": 30,
    "cooldown_minutes": 120,
    "snooze_until": None,
    "last_nudge": None,
    "pending": False,
    "ignored_in_row": 0,
    "sessions": {},
    "log": [],
}
RESET_KINDS = ("question", "challenge")
COUNT_KINDS = ("directive", "approval", "context")
MAX_LOG = 300
MAX_SESSIONS = 50

CONTROLS = "Enter: send anyway · /mirror:snooze: pause nudges · /mirror:off: turn off"
COPY = [
    "Mirror held this message. Nothing is broken. {n} messages without a question. Review Claude's last answer?\n" + CONTROLS,
    "Mirror held this message. Nothing is broken. {n} messages without a question or pushback. Review Claude's last answer?\n" + CONTROLS,
]
INTRO = ("Mirror nudges are off. Type /mirror:on to turn them on. "
         "Mirror counts your messages but never stores or sends what you write.")
STEP_BACK = ("No answer to the last 3 nudges, so Mirror will stay quiet for a day.\n"
             "/mirror:on: resume · /mirror:off: turn off")


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
    return store.home() / "nudge.json"


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
    sess = st.get("sessions", {})
    if len(sess) > MAX_SESSIONS:
        keep = sorted(sess.items(), key=lambda kv: kv[1].get("seen", ""))[-MAX_SESSIONS:]
        st["sessions"] = dict(keep)
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    tmp.replace(_path())


def _log(st, event, **kw):
    st.setdefault("log", []).append(dict({"at": _iso(_now()), "event": event}, **kw))


def _close_pending(st, response):
    if st.get("pending"):
        st["pending"] = False
        _log(st, "response", response=response)
        if response in ("check", "snooze", "off", "acted", "edited"):
            st["ignored_in_row"] = 0
        elif response == "sent_anyway":
            st["ignored_in_row"] = st.get("ignored_in_row", 0) + 1


def on_prompt(session_id, prompt, now=None):
    """Called once per user prompt. Returns the one line to show the user, or None."""
    now = now or _now()
    st = load()
    kind = classify(prompt or "")
    # A /mirror:* command is the user answering Mirror; handled by the command itself.
    if (prompt or "").lstrip().startswith("/mirror"):
        return None
    if not st["enabled"]:
        if not st["introduced"]:
            st["introduced"] = True
            save(st)
            return INTRO
        return None
    if kind not in RESET_KINDS + COUNT_KINDS:
        return None  # commands, pasted text: not counted
    if st.get("pending"):
        _close_pending(st, "acted" if kind in RESET_KINDS else "sent_anyway" if kind == "approval" else "edited")
    sess = st["sessions"].setdefault(session_id or "default", {"streak": 0})
    sess["seen"] = _iso(now)
    sess["streak"] = 0 if kind in RESET_KINDS else sess.get("streak", 0) + 1
    msg = None
    snooze = _parse(st.get("snooze_until"))
    last = _parse(st.get("last_nudge"))
    mult = 2 ** min(st.get("ignored_in_row", 0), 3)
    cool = timedelta(minutes=st["cooldown_minutes"] * mult)
    ready = (snooze is None or now >= snooze) and (last is None or now - last >= cool)
    if sess["streak"] >= st["threshold"] and ready:
        if st.get("pending"):
            st["ignored_in_row"] = st.get("ignored_in_row", 0) + 1
            _log(st, "response", response="ignored")
            st["pending"] = False
        if st["ignored_in_row"] >= 3:
            st["snooze_until"] = _iso(now + timedelta(days=1))
            st["ignored_in_row"] = 0
            _log(st, "step_back")
            msg = STEP_BACK
        else:
            n = sess["streak"]
            msg = COPY[len([e for e in st["log"] if e["event"] == "nudge"]) % len(COPY)].format(n=n)
            st["pending"] = True
            st["last_nudge"] = _iso(now)
            _log(st, "nudge", streak=n)
        sess["streak"] = 0
    save(st)
    return msg


def respond(action, minutes=None, now=None):
    """User answers: on, off, snooze, check. Returns a short confirmation line."""
    now = now or _now()
    st = load()
    if action == "on":
        st["enabled"], st["introduced"], st["snooze_until"] = True, True, None
        _log(st, "on")
        out = (f"Mirror nudges are on. You'll see one line after {st['threshold']} messages without a question "
               f"or pushback, at most once every {st['cooldown_minutes'] // 60} hours. /mirror:off stops them.")
    elif action == "off":
        _close_pending(st, "off")
        st["enabled"] = False
        _log(st, "off")
        out = "Mirror nudges are off. /mirror:on turns them back on."
    elif action == "snooze":
        _close_pending(st, "snooze")
        mins = minutes or st["cooldown_minutes"]
        st["snooze_until"] = _iso(now + timedelta(minutes=mins))
        _log(st, "snooze", minutes=mins)
        out = f"Mirror is quiet for {mins // 60 if mins >= 60 else mins} {'hours' if mins >= 60 else 'minutes'}."
    elif action == "check":
        _close_pending(st, "check")
        _log(st, "check")
        out = "check started"
    else:
        return "Unknown action."
    save(st)
    return out


def status():
    st = load()
    nudges = [e for e in st["log"] if e["event"] == "nudge"]
    responses = [e.get("response") for e in st["log"] if e["event"] == "response"]
    lines = [
        f"Nudges: {'on' if st['enabled'] else 'off'}; threshold {st['threshold']} messages; cooldown {st['cooldown_minutes']} min"
        + (f" x{2 ** min(st['ignored_in_row'], 3)} (after ignored nudges)" if st.get("ignored_in_row") else ""),
        f"Snoozed until: {st['snooze_until'] or '-'}",
        f"Nudges shown: {len(nudges)}; answered with check {responses.count('check')}, snooze {responses.count('snooze')}, "
        f"off {responses.count('off')}; acted (asked or pushed back) {responses.count('acted')}; "
        f"edited {responses.count('edited')}; sent anyway {responses.count('sent_anyway')}; ignored {responses.count('ignored')}",
    ]
    return "\n".join(lines)


def hook_main(stdin_text):
    """Entry point for the UserPromptSubmit hook. A nudge blocks the prompt with its line as the reason;
    the intro and step-back lines go out as systemMessage. Anything else prints nothing."""
    try:
        data = json.loads(stdin_text or "{}")
        # Claude Code sends "prompt"; the docs name it "user_prompt". Accept both.
        msg = on_prompt(data.get("session_id"), data.get("prompt") or data.get("user_prompt") or "")
        if msg in (INTRO, STEP_BACK):
            return json.dumps({"systemMessage": msg})
        if msg:
            return json.dumps({"decision": "block", "reason": msg})
    except Exception:  # never break the user's prompt
        return ""
    return ""
