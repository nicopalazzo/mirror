"""Readers for local AI logs. Read-only. Only session files are ever opened.

Claude Code: <claude dir>/projects/<project>/<session>.jsonl
Codex:       <codex dir>/sessions/**/rollout-*.jsonl and <codex dir>/archived_sessions/rollout-*.jsonl
Nothing else in those folders (credentials, settings, databases) is opened.
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path

from .model import Turn, Action
from .timeutil import parse_ts

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
META_START = re.compile(r"^\s*(<command-|<local-command|<task-|\[Request interrupted)")


def default_dirs():
    claude = os.environ.get("MIRROR_CLAUDE_DIR") or os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    codex = os.environ.get("MIRROR_CODEX_DIR") or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(claude), Path(codex)


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
        session, project = f.stem, f.parent.name
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
                turns.append(Turn(ts, "Claude", session, project, chars=len(text), text=text))
            elif t == "assistant":
                msg = r.get("message") or {}
                model = msg.get("model") or "claude"
                mid = msg.get("id")
                if mid and mid not in seen:
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
        rows = list(_lines(f))
        if not rows:
            continue
        m = re.search(r"rollout-[\dT-]+-(.+)\.jsonl$", f.name)
        session = m.group(1) if m else f.stem
        project = "codex"
        model = next(((r.get("payload") or {}).get("model") for r in rows if r.get("type") == "turn_context"), None) or "codex"
        for r in rows:
            if r.get("type") == "session_meta":
                cwd = (r.get("payload") or {}).get("cwd")
                if cwd:
                    project = cwd
                break
        has_event_users = any(r.get("type") == "event_msg" and (r.get("payload") or {}).get("type") == "user_message" for r in rows)
        last_tok = None
        for r in rows:
            ts = parse_ts(r.get("timestamp"))
            if ts is None:
                continue
            p = r.get("payload") or {}
            pt = p.get("type")
            t = r.get("type")
            if t == "event_msg" and pt == "user_message" and has_event_users:
                text = (p.get("message") or "").strip()
                if text:
                    turns.append(Turn(ts, "Codex", session, project, chars=len(text), text=text))
            elif t == "response_item" and pt == "message":
                text = " ".join(c.get("text", "") for c in p.get("content", []) if isinstance(c, dict)).strip()
                if p.get("role") == "user" and not has_event_users:
                    if text and not text.startswith("<") and not text.startswith("# AGENTS.md"):
                        turns.append(Turn(ts, "Codex", session, project, chars=len(text), text=text))
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


def inventory(claude_root: Path, codex_root: Path):
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
    return {
        "Claude Code": dict(path=str(claude_root / "projects"), **summ(claude_files(claude_root))),
        "Codex": dict(path=str(codex_root / "sessions") + " (+ archived_sessions)", **summ(codex_files(codex_root))),
    }
