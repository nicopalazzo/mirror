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
- Two firing rules (5 Oct 2026). "streak": N messages in a row without a question or pushback.
  "ratio": the share of passive messages (directive, approval, context) over the last `window`
  counted messages reaches `ratio_threshold`; one question no longer resets everything.
- Hold-back experiment (5 Oct 2026). With `holdback` > 0, each time the rule fires a coin decides
  whether the nudge is shown or silently held back. The next message is logged as the response in
  both arms, so the acted rate after a shown nudge can be compared with the same moment without one.
  Held-back moments start the cooldown but never count as ignored. Off (0.0) by default.
- A nudge blocks that one prompt and shows its line where the user is typing; the prompt stays in
  the input box, so Enter sends it. Claude Code does not display systemMessage from this hook
  (tested 26 Sep 2026, v2.1.283, Desktop app and CLI), so blocking is the only direct channel.
- Any error: exit silently. A broken hook must never block or slow the user's prompt.
"""
from __future__ import annotations
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    "pending_arm": None,
    "ignored_in_row": 0,
    "rule": "streak",
    "window": 20,
    "ratio_threshold": 0.9,
    "holdback": 0.0,
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
COPY_RATIO = ("Mirror held this message. Nothing is broken. {k} of your last {w} messages had no question or pushback. "
              "Review Claude's last answer?\n" + CONTROLS)
INTRO = ("Mirror nudges are off. Type /mirror:on to turn them on. "
         "Mirror counts your messages but never stores or sends what you write.")
STEP_BACK = ("No answer to the last 3 nudges, so Mirror will stay quiet for a day.\n"
             "/mirror:on: resume · /mirror:off: turn off")


_rand = random.random  # replaced in tests


def localize(text):
    """Codex plugin copies carry a .codex-plugin folder next to mirror_core: say $mirror:x, not /mirror:x."""
    if not text or not (Path(__file__).resolve().parent.parent / ".codex-plugin").exists():
        return text
    return text.replace("/mirror:", "$mirror:").replace("Claude's last answer", "the last answer")


def _dur(mins):
    if mins >= 60 and mins % 60 == 0:
        h = mins // 60
        return f"{h} hour" + ("s" if h > 1 else "")
    return f"{mins} minutes"


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
        arm = st.get("pending_arm") or "shown"
        st["pending"] = False
        st["pending_arm"] = None
        _log(st, "response", response=response, arm=arm)
        if arm != "shown":
            return  # the user saw nothing, so nothing was ignored or answered
        if response in ("check", "snooze", "off", "acted", "edited"):
            st["ignored_in_row"] = 0
        elif response in ("sent_anyway", "ignored"):
            st["ignored_in_row"] = st.get("ignored_in_row", 0) + 1


def on_prompt(session_id, prompt, now=None):
    """Called once per user prompt. Returns the one line to show the user, or None."""
    now = now or _now()
    st = load()
    kind = classify(prompt or "")
    # A /mirror:* command is the user answering Mirror; handled by the command itself.
    if (prompt or "").lstrip().startswith(("/mirror", "$mirror")):
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
    active = kind in RESET_KINDS
    sess["streak"] = 0 if active else sess.get("streak", 0) + 1
    window = int(st.get("window") or 20)
    recent = (sess.get("recent") or []) + [0 if active else 1]
    sess["recent"] = recent[-window:]
    r = sum(sess["recent"]) / len(sess["recent"])
    rule = st.get("rule") or "streak"
    if rule == "ratio":
        hit = len(sess["recent"]) >= window and r >= float(st.get("ratio_threshold") or 0.9)
    else:
        hit = sess["streak"] >= st["threshold"]
    msg = None
    snooze = _parse(st.get("snooze_until"))
    last = _parse(st.get("last_nudge"))
    mult = 2 ** min(st.get("ignored_in_row", 0), 3)
    cool = timedelta(minutes=st["cooldown_minutes"] * mult)
    ready = (snooze is None or now >= snooze) and (last is None or now - last >= cool)
    if hit and ready:
        _close_pending(st, "ignored")
        if st["ignored_in_row"] >= 3:
            st["snooze_until"] = _iso(now + timedelta(days=1))
            st["ignored_in_row"] = 0
            _log(st, "step_back")
            msg = STEP_BACK
        else:
            n = sess["streak"]
            k, w = sum(sess["recent"]), len(sess["recent"])
            info = {"rule": rule, "streak": n, "r": round(r, 2)}
            st["pending"] = True
            st["last_nudge"] = _iso(now)
            if _rand() < float(st.get("holdback") or 0.0):
                st["pending_arm"] = "held"
                _log(st, "withheld", **info)
            else:
                st["pending_arm"] = "shown"
                if rule == "ratio":
                    msg = COPY_RATIO.format(k=k, w=w)
                else:
                    msg = COPY[len([e for e in st["log"] if e["event"] == "nudge"]) % len(COPY)].format(n=n)
                _log(st, "nudge", **info)
        sess["streak"] = 0
        sess["recent"] = []
    save(st)
    return msg


def respond(action, minutes=None, now=None):
    """User answers: on, off, snooze, check. Returns a short confirmation line."""
    now = now or _now()
    st = load()
    if action == "on":
        st["enabled"], st["introduced"], st["snooze_until"] = True, True, None
        _log(st, "on")
        if st.get("rule") == "ratio":
            when = (f"when at least {round(100 * float(st['ratio_threshold']))}% of your last {st['window']} messages "
                    f"had no question or pushback")
        else:
            when = f"after {st['threshold']} messages without a question or pushback"
        out = (f"Mirror nudges are on. You'll see one line {when}, at most once every "
               f"{_dur(st['cooldown_minutes'])}. /mirror:off stops them.")
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


SETTINGS = {
    "holdback": (float, 0.0, 0.9, "share of firings held back as a comparison"),
    "rule": (str, None, None, "streak or ratio"),
    "ratio-threshold": (float, 0.5, 1.0, "share of passive messages that fires the ratio rule"),
    "window": (int, 5, 100, "messages the ratio rule looks back over"),
    "threshold": (int, 3, 500, "messages in a row for the streak rule"),
    "cooldown": (int, 5, 1440, "minimum minutes between firings"),
}
_KEYS = {"ratio-threshold": "ratio_threshold", "cooldown": "cooldown_minutes"}


def configure(name, value):
    """Change one nudge setting. Returns a short confirmation or an error line."""
    if name not in SETTINGS:
        return f"Unknown setting: {name}. Settings: {', '.join(SETTINGS)}."
    typ, lo, hi, what = SETTINGS[name]
    try:
        v = typ(value)
        if typ is str:
            if v not in ("streak", "ratio"):
                raise ValueError
        elif not lo <= v <= hi:
            raise ValueError
    except (TypeError, ValueError):
        rng = "streak or ratio" if typ is str else f"{lo} to {hi}"
        return f"{name} must be {rng} ({what})."
    st = load()
    st[_KEYS.get(name, name)] = v
    _log(st, "config", setting=name, value=v)
    save(st)
    return f"{name} set to {v}."


def _arm_line(log, holdback):
    by = {"shown": [], "held": []}
    for e in log:
        if e["event"] == "response" and e.get("arm"):  # responses from before the test carry no arm
            by.setdefault(e["arm"], []).append(e.get("response"))
    if not by["held"] and not holdback:
        return None

    def rates(rs):
        if not rs:
            return "no answers yet", None
        acted = sum(1 for r in rs if r in ("acted", "check"))
        both = acted + rs.count("edited")
        return f"{len(rs)} moments, acted {round(100 * acted / len(rs))}%, acted or edited {round(100 * both / len(rs))}%", acted / len(rs)

    s_txt, s_r = rates(by["shown"])
    h_txt, h_r = rates(by["held"])
    line = f"Hold-back test ({round(100 * holdback)}% held back): shown {s_txt}; held back {h_txt}"
    if s_r is not None and h_r is not None:
        line += f"; difference in acted rate {round(100 * (s_r - h_r)):+d} points (small samples: a direction, not a result)"
    return line


def status():
    st = load()
    nudges = [e for e in st["log"] if e["event"] == "nudge"]
    responses = [e.get("response") for e in st["log"] if e["event"] == "response" and (e.get("arm") or "shown") == "shown"]
    if st.get("rule") == "ratio":
        rule = f"rule: {round(100 * float(st['ratio_threshold']))}% passive over last {st['window']} messages"
        latest = max(st.get("sessions", {}).values(), key=lambda s: s.get("seen", ""), default=None)
        if latest and latest.get("recent"):
            rec = latest["recent"]
            rule += f" (now {round(100 * sum(rec) / len(rec))}% over {len(rec)})"
    else:
        rule = f"rule: {st['threshold']} messages in a row"
    lines = [
        f"Nudges: {'on' if st['enabled'] else 'off'}; {rule}; cooldown {st['cooldown_minutes']} min"
        + (f" x{2 ** min(st['ignored_in_row'], 3)} (after ignored nudges)" if st.get("ignored_in_row") else ""),
        f"Snoozed until: {st['snooze_until'] or '-'}",
        f"Nudges shown: {len(nudges)}; answered with check {responses.count('check')}, snooze {responses.count('snooze')}, "
        f"off {responses.count('off')}; acted (asked or pushed back) {responses.count('acted')}; "
        f"edited {responses.count('edited')}; sent anyway {responses.count('sent_anyway')}; ignored {responses.count('ignored')}",
    ]
    arm = _arm_line(st["log"], float(st.get("holdback") or 0.0))
    if arm:
        lines.append(arm)
    return "\n".join(lines)


def hook_main(stdin_text):
    """Entry point for the UserPromptSubmit hook. A nudge blocks the prompt with its line as the reason;
    the intro and step-back lines go out as systemMessage. Anything else prints nothing."""
    try:
        data = json.loads(stdin_text or "{}")
        # Claude Code sends "prompt"; the docs name it "user_prompt". Accept both.
        msg = on_prompt(data.get("session_id"), data.get("prompt") or data.get("user_prompt") or "")
        if msg in (INTRO, STEP_BACK):
            return json.dumps({"systemMessage": localize(msg)})
        if msg:
            return json.dumps({"decision": "block", "reason": localize(msg)})
    except Exception:  # never break the user's prompt
        return ""
    return ""
