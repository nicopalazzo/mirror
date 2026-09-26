"""Single-file HTML report. No external resources, no network: a strict CSP blocks them in the browser too."""
from __future__ import annotations
import json
from pathlib import Path

from .explain import INDEXES, DISCLAIMER


def build(all_days, feedback, tokens, out_path: Path):
    days = []
    for d, s in all_days.items():
        row = {k: v for k, v in s.items() if k != "_counts"}
        row["date"] = d.isoformat()
        days.append(row)
    data = {"days": days, "feedback": feedback, "tokens": tokens, "indexes": INDEXES, "disclaimer": DISCLAIMER}
    tpl = (Path(__file__).parent / "report_template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", json.dumps(data).replace("</", "<\\/"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
