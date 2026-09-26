"""Synthetic logs in the shapes Claude Code and Codex write. No real conversations anywhere in this repo."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build(root: Path, base=None):
    """Creates root/claude and root/codex. Returns (claude_dir, codex_dir, base_datetime)."""
    base = base or datetime.now().astimezone().replace(hour=9, minute=0, second=0, microsecond=0)
    claude, codex = root / "claude", root / "codex"
    proj = claude / "projects" / "-home-demo-app"
    proj.mkdir(parents=True)
    rows = []
    t = base

    def user(text, dt):
        rows.append({"type": "user", "timestamp": _z(dt), "cwd": "/home/demo/app", "message": {"role": "user", "content": text}})

    def asst(blocks, dt, mid):
        rows.append({"type": "assistant", "timestamp": _z(dt), "message": {"id": mid, "model": "claude-test-1", "role": "assistant",
                     "content": blocks, "usage": {"input_tokens": 10, "output_tokens": 50, "cache_read_input_tokens": 100}}})

    user("Can you add a login page?", t)
    asst([{"type": "text", "text": "Sure."}, {"type": "tool_use", "id": "a", "name": "Write", "input": {"file_path": "x"}}], t + timedelta(seconds=20), "m1")
    asst([{"type": "tool_use", "id": "b", "name": "Edit", "input": {}}], t + timedelta(seconds=30), "m2")
    user("ok", t + timedelta(seconds=35))  # quick approval: 5 s after file changes
    asst([{"type": "tool_use", "id": "c", "name": "Read", "input": {}}, {"type": "text", "text": "Done."}], t + timedelta(seconds=60), "m3")
    user("Pourquoi tu as oublié le bouton de déconnexion ?", t + timedelta(minutes=3))
    asst([{"type": "tool_use", "id": "d", "name": "Write", "input": {}}], t + timedelta(minutes=3, seconds=20), "m4")
    user("Parfait, merci", t + timedelta(minutes=6))  # slow approval
    user("What is the difference between a cookie and a token?", t + timedelta(minutes=9))
    asst([{"type": "text", "text": "A cookie is..."}], t + timedelta(minutes=9, seconds=15), "m5")
    user("<command-name>/model</command-name>", t + timedelta(minutes=10))
    user("I think we should keep the design simple.", t + timedelta(minutes=11))
    rows.append({"type": "user", "timestamp": _z(t + timedelta(minutes=12)), "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}})
    (proj / "sess-1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    sess = codex / "sessions" / t.strftime("%Y/%m/%d")
    sess.mkdir(parents=True)
    c = base + timedelta(hours=2)
    crow = [
        {"timestamp": _z(c), "type": "session_meta", "payload": {"cwd": "/home/demo/other"}},
        {"timestamp": _z(c), "type": "turn_context", "payload": {"model": "codex-test"}},
        {"timestamp": _z(c + timedelta(seconds=1)), "type": "event_msg", "payload": {"type": "user_message", "message": "Write a script that renames files"}},
        {"timestamp": _z(c + timedelta(seconds=5)), "type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "On it"}]}},
        {"timestamp": _z(c + timedelta(seconds=8)), "type": "response_item", "payload": {"type": "custom_tool_call", "name": "apply_patch", "input": "*** Begin Patch\n*** Add File: a.py\n+x"}},
        {"timestamp": _z(c + timedelta(seconds=9)), "type": "event_msg", "payload": {"type": "user_message", "message": "yes go ahead"}},
        {"timestamp": _z(c + timedelta(seconds=15)), "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 50}}}},
    ]
    (sess / "rollout-2026-01-01T00-00-00-abc-123.jsonl").write_text("\n".join(json.dumps(r) for r in crow) + "\n", encoding="utf-8")

    # Cursor: a time only on the human's messages; a subagent transcript that must be ignored.
    off = base.utcoffset()
    mins = int(off.total_seconds() // 60)
    tz = "UTC%+d" % (mins // 60) if mins % 60 == 0 else "UTC%+d:%02d" % (mins // 60, abs(mins) % 60)
    d0 = base.replace(hour=10)
    def cts(dt):
        return "%s, %s %d, %d, %d:%02d %s (%s)" % (dt.strftime("%A"), dt.strftime("%b"), dt.day, dt.year, (dt.hour % 12) or 12, dt.minute, "AM" if dt.hour < 12 else "PM", tz)
    def cu(q, dt):
        return {"role": "user", "message": {"content": [{"type": "text", "text": "<timestamp>%s</timestamp>\n<user_query>\n%s\n</user_query>" % (cts(dt), q)}]}}
    def ca(blocks):
        return {"role": "assistant", "message": {"content": blocks}}
    chat = codex.parent / "cursor" / "projects" / "demo" / "agent-transcripts" / "chat-1"
    (chat / "subagents").mkdir(parents=True)
    crow2 = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "<timestamp>%s</timestamp>" % cts(d0)}]}},  # timestamp-only row: not a message
        cu("Please build the settings page", d0),
        ca([{"type": "text", "text": "Working."}, {"type": "tool_use", "name": "Read", "input": {}}, {"type": "tool_use", "name": "StrReplace", "input": {}}]),
        cu("ok", d0 + timedelta(minutes=2)),
        ca([{"type": "tool_use", "name": "WebSearch", "input": {}}]),
        cu("Pourquoi tu as oublié le fichier de configuration ?", d0 + timedelta(minutes=5)),
        {"status": "x", "type": "error"},
    ]
    (chat / "chat-1.jsonl").write_text("\n".join(json.dumps(r) for r in crow2) + "\n", encoding="utf-8")
    (chat / "subagents" / "sub-1.jsonl").write_text(json.dumps(cu("SUBAGENT PROMPT do not count", d0)) + "\n", encoding="utf-8")
    cursor = codex.parent / "cursor"
    (cursor / "mcp.json").write_text('{"token": "do-not-read"}', encoding="utf-8")
    (cursor / "projects" / "demo" / "canvases").mkdir()
    (cursor / "projects" / "demo" / "canvases" / "x.canvas.tsx").write_text("do-not-read", encoding="utf-8")

    # Decoys: files Mirror must never open.
    (claude / "settings.json").write_text('{"secret": "do-not-read"}', encoding="utf-8")
    (claude / "projects" / "notes.txt").write_text("do-not-read", encoding="utf-8")
    (codex / "auth.json").write_text('{"token": "do-not-read"}', encoding="utf-8")
    (codex / "config.toml").write_text("do-not-read", encoding="utf-8")
    return claude, codex, base


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1])
    build(out)
    print("fixtures written to " + str(out))
