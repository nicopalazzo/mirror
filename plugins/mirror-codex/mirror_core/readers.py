"""Readers for local AI logs. Read-only. Only session files are ever opened.

Claude Code: <claude dir>/projects/<project>/<session>.jsonl
Codex:       <codex dir>/sessions/**/rollout-*.jsonl and <codex dir>/archived_sessions/rollout-*.jsonl
Cursor:      <cursor dir>/projects/<project>/agent-transcripts/<chat>/<chat>.jsonl (not the subagents folder)
Nothing else in those folders (credentials, settings, databases) is opened.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import time
from pathlib import Path

from .classify import classify
from .model import Turn, Action
from .timeutil import parse_ts

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
META_START = re.compile(r"^\s*(<command-|<local-command|<task-|\[Request interrupted)")


def _pid(value):
    """Project folders and paths are only ever used to count distinct projects, so keep a short hash, not the name."""
    return hashlib.sha256(str(value).encode("utf-8", "replace")).hexdigest()[:8]


def _turn(ts, tool, session, project, text):
    """Label a message and drop its text immediately. Returns None for commands and other non-messages."""
    kind = classify(text)
    if kind == "meta":
        return None
    return Turn(ts, tool, session, project, kind=kind, chars=len(text))


def default_dirs():
    claude = os.environ.get("MIRROR_CLAUDE_DIR") or os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    codex = os.environ.get("MIRROR_CODEX_DIR") or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    cursor = os.environ.get("MIRROR_CURSOR_DIR") or str(Path.home() / ".cursor")
    return Path(claude), Path(codex), Path(cursor)


def claude_files(root: Path):
    proj = root / "projects"
    if not proj.is_dir():
        return []
    return sorted(proj.glob("*/*.jsonl"))


def codex_files(root: Path):
    out = []
    s = root / "sessions"
    if s.is_dir():
        out += list(s.glob("*/*/*/rollout-*.jsonl"))
    a = root / "archived_sessions"
    if a.is_dir():
        out += list(a.glob("rollout-*.jsonl"))
    return sorted(out)


def cursor_files(root: Path):
    proj = root / "projects"
    if not proj.is_dir():
        return []
    return sorted(set(proj.glob("*/agent-transcripts/*/*.jsonl")) | set(proj.glob("*/agent-transcripts/*.jsonl")))


def _recent(path: Path, since_days):
    if since_days is None:
        return True
    try:
        return path.stat().st_mtime >= time.time() - since_days * 86400
    except OSError:
        return False


def _lines(path: Path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def _claude_cat(name):
    if name in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        return "write"
    if name in ("Read", "Glob", "Grep", "ToolSearch", "LS"):
        return "read"
    if name in ("WebSearch", "WebFetch") or "browser" in name.lower():
        return "research"
    return "shell"


def read_claude(root: Path, since_days=None):
    turns, actions, tokens = [], [], {}
    for f in claude_files(root):
        if not _recent(f, since_days):
            continue
        session, project = f.stem, _pid(f.parent.name)
        seen = set()
        for r in _lines(f):
            if not isinstance(r, dict) or r.get("isSidechain"):
                continue
            ts = parse_ts(r.get("timestamp"))
            if ts is None:
                continue
            t = r.get("type")
            if t == "user" and not r.get("isMeta"):
                msg = r.get("message") or {}
                c = msg.get("content")
                if isinstance(c, list):
                    if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                        continue
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                if not isinstance(c, str):
                    continue
                text = REMINDER.sub("", c).strip()
                if not text:
                    continue
                turn = _turn(ts, "Claude", session, project, text)
                if turn:
                    turns.append(turn)
            elif t == "assistant":
                msg = r.get("message") or {}
                model = msg.get("model") or "claude"
                mid = msg.get("id")
                if mid and mid not in seen and not str(model).startswith("<"):
                    seen.add(mid)
                    u = msg.get("usage") or {}
                    d = tokens.setdefault(model, {"messages": 0, "output": 0, "input": 0, "cached": 0})
                    d["messages"] += 1
                    d["output"] += u.get("output_tokens", 0) or 0
                    d["input"] += (u.get("input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)
                    d["cached"] += u.get("cache_read_input_tokens", 0) or 0
                content = msg.get("content")
                if isinstance(content, str):
                    if content.strip():
                        actions.append(Action(ts, "Claude", session, project, model, "reply"))
                    continue
                for x in content or []:
                    if not isinstance(x, dict):
                        continue
                    if x.get("type") == "text" and (x.get("text") or "").strip():
                        actions.append(Action(ts, "Claude", session, project, model, "reply"))
                    elif x.get("type") == "tool_use":
                        actions.append(Action(ts, "Claude", session, project, model, _claude_cat(x.get("name", ""))))
    return turns, actions, tokens


_READ = re.compile(r"\b(cat|sed|head|tail|ls|dir|type|get-content|rg|grep|findstr|find|wc|tree)\b", re.I)
_WEB = re.compile(r"\b(curl|wget|invoke-webrequest|web_search|web\.run)\b", re.I)


def _codex_cat(name, body):
    b = f"{name} {body}"
    if "apply_patch" in b or "*** Add File" in b or "*** Update File" in b or "*** Begin Patch" in b:
        return "write"
    if _WEB.search(b):
        return "research"
    if _READ.search(b):
        return "read"
    return "shell"


def read_codex(root: Path, since_days=None):
    turns, actions, tokens = [], [], {}
    for f in codex_files(root):
        if not _recent(f, since_days):
            continue
        # Pass 1: three small facts, streaming, nothing kept. Pass 2 below streams again.
        model, project, has_event_users, any_rows = None, _pid("codex"), False, False
        for r in _lines(f):
            any_rows = True
            p0 = r.get("payload") or {}
            if r.get("type") == "turn_context" and model is None:
                model = p0.get("model")
            elif r.get("type") == "session_meta" and p0.get("cwd") and project == _pid("codex"):
                project = _pid(p0["cwd"])
            elif r.get("type") == "event_msg" and p0.get("type") == "user_message":
                has_event_users = True
        if not any_rows:
            continue
        model = model or "codex"
        m = re.search(r"rollout-[\dT-]+-(.+)\.jsonl$", f.name)
        session = m.group(1) if m else f.stem
        last_tok = None
        for r in _lines(f):
            ts = parse_ts(r.get("timestamp"))
            if ts is None:
                continue
            p = r.get("payload") or {}
            pt = p.get("type")
            t = r.get("type")
            if t == "event_msg" and pt == "user_message" and has_event_users:
                text = (p.get("message") or "").strip()
                if text:
                    turn = _turn(ts, "Codex", session, project, text)
                    if turn:
                        turns.append(turn)
            elif t == "response_item" and pt == "message":
                text = " ".join(c.get("text", "") for c in p.get("content", []) if isinstance(c, dict)).strip()
                if p.get("role") == "user" and not has_event_users:
                    if text and not text.startswith("<") and not text.startswith("# AGENTS.md"):
                        turn = _turn(ts, "Codex", session, project, text)
                        if turn:
                            turns.append(turn)
                elif p.get("role") == "assistant" and text:
                    actions.append(Action(ts, "Codex", session, project, model, "reply"))
            elif t == "response_item" and pt in ("custom_tool_call", "function_call"):
                body = str(p.get("arguments") or p.get("input") or "")
                actions.append(Action(ts, "Codex", session, project, model, _codex_cat(p.get("name", ""), body)))
            elif t == "event_msg" and pt == "token_count" and p.get("info"):
                last_tok = p["info"].get("total_token_usage")
        if last_tok:
            d = tokens.setdefault(model, {"messages": 0, "output": 0, "input": 0, "cached": 0})
            cached = last_tok.get("cached_input_tokens", 0) or 0
            d["messages"] += 1
            d["output"] += last_tok.get("output_tokens", 0) or 0
            d["input"] += (last_tok.get("input_tokens", 0) or 0) - cached
            d["cached"] += cached
    return turns, actions, tokens


_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_CURSOR_TS = re.compile(r"<timestamp>\s*(?:\w+,\s*)?(\w{3})\w*\s+(\d{1,2}),\s*(\d{4}),\s*(\d{1,2}):(\d{2})\s*(AM|PM)\s*(?:\(UTC([+-]\d{1,2})(?::?(\d{2}))?\))?", re.I)
_CURSOR_Q = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
_CURSOR_READ = {"Read", "ReadFile", "Glob", "Grep", "LS", "SemanticSearch", "ReadLints", "GetDynamicTools", "GetMcpTools", "SearchConversations", "rg"}
_CURSOR_WRITE = {"Write", "StrReplace", "ApplyPatch", "Delete", "EditNotebook"}
_CURSOR_WEB = {"WebSearch", "WebFetch"}


def _cursor_ts(text):
    """Cursor writes '<timestamp>Friday, Sep 25, 2026, 1:01 PM (UTC+2)</timestamp>' on each message of yours."""
    from datetime import datetime, timedelta, timezone
    m = _CURSOR_TS.search(text)
    if not m:
        return None
    mon = _MONTHS.get(m.group(1).lower()[:3])
    if not mon:
        return None
    hour = int(m.group(4)) % 12 + (12 if m.group(6).upper() == "PM" else 0)
    try:
        naive = datetime(int(m.group(3)), mon, int(m.group(2)), hour, int(m.group(5)))
    except ValueError:
        return None
    if m.group(7) is not None:
        sign = -1 if m.group(7).startswith("-") else 1
        off = timedelta(hours=abs(int(m.group(7))), minutes=int(m.group(8) or 0)) * sign
        return naive.replace(tzinfo=timezone(off)).astimezone()
    return naive.astimezone()  # no zone written: assume this computer's


def _cursor_cat(name):
    if name in _CURSOR_WRITE:
        return "write"
    if name in _CURSOR_READ:
        return "read"
    if name in _CURSOR_WEB:
        return "research"
    return "shell"


def read_cursor(root: Path, since_days=None):
    """Cursor logs carry a time only on your messages. AI replies and tool calls inherit the time of your latest
    message and are marked untimed, so anything that needs real timing (quick approvals) skips them."""
    turns, actions, tokens = [], [], {}
    for f in cursor_files(root):
        if not _recent(f, since_days):
            continue
        session = f.stem
        parts = f.parts
        project = _pid(parts[parts.index("agent-transcripts") - 1]) if "agent-transcripts" in parts else _pid("cursor")
        last_ts = None
        for r in _lines(f):
            if not isinstance(r, dict):
                continue
            role = r.get("role")
            msg = r.get("message") or {}
            content = msg.get("content")
            if role == "user":
                text = content if isinstance(content, str) else " ".join(x.get("text", "") for x in (content or []) if isinstance(x, dict) and x.get("type") == "text")
                ts = _cursor_ts(text)
                if ts is not None:
                    last_ts = ts
                q = _CURSOR_Q.search(text)
                if q and q.group(1).strip() and last_ts is not None:
                    turn = _turn(last_ts, "Cursor", session, project, q.group(1))
                    if turn:
                        turns.append(turn)
            elif role == "assistant" and last_ts is not None:
                if isinstance(content, str):
                    if content.strip():
                        actions.append(Action(last_ts, "Cursor", session, project, "cursor", "reply", timed=False))
                    continue
                for x in content or []:
                    if not isinstance(x, dict):
                        continue
                    if x.get("type") == "text" and (x.get("text") or "").strip():
                        actions.append(Action(last_ts, "Cursor", session, project, "cursor", "reply", timed=False))
                    elif x.get("type") == "tool_use":
                        actions.append(Action(last_ts, "Cursor", session, project, "cursor", _cursor_cat(x.get("name", "")), timed=False))
    return turns, actions, tokens


def inventory(claude_root: Path, codex_root: Path, cursor_root: Path = None):
    """Counts files by stat() only. Opens nothing."""
    def summ(files):
        total = 0
        newest = 0.0
        for f in files:
            try:
                st = f.stat()
                total += st.st_size
                newest = max(newest, st.st_mtime)
            except OSError:
                pass
        return {"files": len(files), "bytes": total, "newest": newest}
    out = {
        "Claude Code": dict(path=str(claude_root / "projects"), **summ(claude_files(claude_root))),
        "Codex": dict(path=str(codex_root / "sessions") + " (+ archived_sessions)", **summ(codex_files(codex_root))),
    }
    if cursor_root is not None:
        out["Cursor"] = dict(path=str(cursor_root / "projects" / "*" / "agent-transcripts"), **summ(cursor_files(cursor_root)))
    return out
