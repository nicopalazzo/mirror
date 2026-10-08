"""Single-file HTML report. No external resources, no network: a strict CSP blocks them in the browser too."""
from __future__ import annotations
import json
from pathlib import Path

from .explain import INDEXES, DISCLAIMER


TOOL_NOTES = {
    "Cursor": "Cursor logs carry a time only on your messages, so quick approvals cannot be measured for it and active time is approximate.",
}
NOT_READ = [
    "Web chats such as claude.ai and chatgpt.com, which leave no log on this computer.",
    "Anything older than the oldest session file each tool still keeps (Claude Code deletes sessions after about 30 days by default).",
]


def build(all_days, feedback, tokens, out_path: Path, coverage=None):
    days = []
    for d, s in all_days.items():
        row = {k: v for k, v in s.items() if k != "_counts"}
        row["counts"] = s["_counts"]
        row["date"] = d.isoformat()
        days.append(row)
    data = {"days": days, "feedback": feedback, "tokens": tokens, "indexes": INDEXES, "disclaimer": DISCLAIMER,
            "coverage": [dict(c, note=TOOL_NOTES.get(c["tool"], "")) for c in (coverage or [])], "not_read": NOT_READ}
    tpl = (Path(__file__).parent / "report_template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", json.dumps(data).replace("</", "<\\/"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
