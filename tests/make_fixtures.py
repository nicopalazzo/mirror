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
