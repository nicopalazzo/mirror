"""Opt-in, numbers-only cards and group ranges, computed locally."""
from __future__ import annotations

import html
import json
import math
import re
import statistics
from datetime import timedelta
from pathlib import Path

from . import __version__
from .explain import TEAM_CANNOT, DISCLAIMER

CARD_KIND = "mirror-team-card"
CARD_VERSION = 1
MIN_CARDS = 5
MIN_MESSAGES = 20
MIN_APPROVALS = 5
NUMBER_KEYS = ("question_or_pushback_pct", "quick_approval_pct", "actions_per_message",
               "longest_write_run", "active_minutes_per_day")
LABELS = dict(zip(NUMBER_KEYS, (
    ("Messages that ask a question or push back", "%"),
    ("Approvals within 15 s of a file change", "%"),
    ("AI actions per message", ""),
    ("Longest run of file changes with no message in between", ""),
    ("Active minutes per active day", " min"))))
BOUNDS = dict(zip(NUMBER_KEYS, ((0, 100), (0, 100), (0, 1000), (0, 100000), (0, 1440))))


class TooFewCards(ValueError):
    def __init__(self, n):
        self.n = n
        super().__init__(n)


def build_card(all_days, end_date, days=28):
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError("days must be between 1 and 366")
    selected = [s for d, s in all_days.items() if end_date - timedelta(days=days) < d <= end_date]
    msgs = sum(s["_counts"]["engaged"] for s in selected)
    qp = sum(s["_counts"]["question"] + s["_counts"]["challenge"] for s in selected)
    quick = sum(s["idx"]["quick_approvals"] for s in selected)
    aaw = sum(s["idx"]["approvals_after_writes"] for s in selected)
    acts = sum(s["ai_actions"] for s in selected)
    run = max((s["idx"]["longest_write_run"] for s in selected), default=0)
    minutes = sum(s["active_minutes"] for s in selected)
    active_days = sum(bool(s["_counts"]["engaged"] or s["ai_actions"]) for s in selected)
    year, week, _ = end_date.isocalendar()
    return {"kind": CARD_KIND, "card_version": CARD_VERSION, "mirror_version": __version__,
            "period": {"days": days, "ending_week": f"{year:04d}-W{week:02d}"},
            "numbers": dict(zip(NUMBER_KEYS, (
                round(100 * qp / msgs) if msgs >= MIN_MESSAGES else None,
                round(100 * quick / aaw) if aaw >= MIN_APPROVALS else None,
                round(acts / msgs, 1) if msgs >= MIN_MESSAGES else None,
                int(run), int(5 * round(minutes / active_days / 5)) if active_days else None)))}


def _shape(obj, keys):
    return isinstance(obj, dict) and set(obj) == set(keys)


def _version(value):
    return isinstance(value, str) and len(value) <= 32 and re.fullmatch(r"\d+\.\d+\.\d+", value, re.ASCII) is not None


def _week(value):
    return isinstance(value, str) and re.fullmatch(r"\d{4}-W\d{2}", value, re.ASCII) is not None


def _number(value, key):
    return type(value) in (int, float) and BOUNDS[key][0] <= value <= BOUNDS[key][1]


def validate_card(obj):
    if not _shape(obj, ("kind", "card_version", "mirror_version", "period", "numbers")):
        return None
    if obj["kind"] != CARD_KIND or type(obj["card_version"]) is not int or obj["card_version"] != CARD_VERSION or not _version(obj["mirror_version"]):
        return None
    p = obj["period"]
    if not _shape(p, ("days", "ending_week")) or type(p["days"]) is not int or not 1 <= p["days"] <= 366 or not _week(p["ending_week"]):
        return None
    if not _shape(obj["numbers"], NUMBER_KEYS):
        return None
    if any(v is not None and not _number(v, k) for k, v in obj["numbers"].items()):
        return None
    return {**obj, "period": dict(p), "numbers": {k: obj["numbers"][k] for k in NUMBER_KEYS}}


def load_cards(folder):
    cards, skipped = [], 0
    for path in sorted(folder.glob("*.json")):
        try:
            if not path.is_file() or path.stat().st_size > 64 * 1024:
                skipped += 1
                continue
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError):
            skipped += 1
            continue
        for item in obj if isinstance(obj, list) else [obj]:
            card = validate_card(item)
            if card is None:
                skipped += 1
            else:
                cards.append(card)
    return cards, skipped


def summarize(cards):
    if len(cards) < MIN_CARDS:
        raise TooFewCards(len(cards))
    numbers = {}
    for k in NUMBER_KEYS:
        values = [c["numbers"][k] for c in cards if c["numbers"][k] is not None]
        if len(values) < MIN_CARDS:
            numbers[k] = {"n": len(values), "too_few": True}
        else:
            a, m, b = statistics.quantiles(values, n=4, method="inclusive")
            rounded = lambda v: round(v, 1) if k == "actions_per_message" else round(v)
            numbers[k] = {"n": len(values), "median": rounded(m), "p25": rounded(a), "p75": rounded(b)}
    return {"kind": "mirror-team-summary", "summary_version": 1, "cards": len(cards),
            "weeks": sorted({c["period"]["ending_week"] for c in cards}),
            "versions": sorted({c["mirror_version"] for c in cards}), "numbers": numbers}


def validate_summary(obj):
    if not _shape(obj, ("kind", "summary_version", "cards", "weeks", "versions", "numbers")):
        return None
    if obj["kind"] != "mirror-team-summary" or type(obj["summary_version"]) is not int or obj["summary_version"] != 1:
        return None
    if type(obj["cards"]) is not int or obj["cards"] < MIN_CARDS:
        return None
    for name, check in (("weeks", _week), ("versions", _version)):
        values = obj[name]
        if not isinstance(values, list) or not values or len(values) > obj["cards"] or not all(check(v) for v in values):
            return None
        if values != sorted(set(values)):
            return None
    if not _shape(obj["numbers"], NUMBER_KEYS):
        return None
    numbers = {}
    for k, row in obj["numbers"].items():
        if not isinstance(row, dict) or type(row.get("n")) is not int or not 0 <= row["n"] <= obj["cards"]:
            return None
        if row["n"] < MIN_CARDS:
            if not _shape(row, ("n", "too_few")) or row["too_few"] is not True:
                return None
        elif not _shape(row, ("n", "median", "p25", "p75")) or not all(_number(row[x], k) for x in ("median", "p25", "p75")) or not row["p25"] <= row["median"] <= row["p75"]:
            return None
        numbers[k] = dict(row)
    return {**obj, "weeks": list(obj["weeks"]), "versions": list(obj["versions"]), "numbers": numbers}


def place(mine_card, summary):
    lines = []
    for k in NUMBER_KEYS:
        label, unit = LABELS[k]
        v, row = mine_card["numbers"][k], summary["numbers"][k]
        if v is None or row.get("too_few"):
            lines.append(f"{label}: not enough to compare.")
        else:
            position = "below" if v < row["p25"] else "above" if v > row["p75"] else "inside"
            lines.append(f"{label}: yours {v}{unit}. Team middle half {row['p25']}–{row['p75']}{unit}, median {row['median']}{unit}. Yours is {position} the middle half.")
    return lines


def _subtitle(summary):
    w = summary["weeks"]
    weeks = f"week {w[0]}" if len(w) == 1 else f"weeks {w[0]}–{w[-1]}"
    return f"{summary['cards']} cards, {weeks}, Mirror {', '.join(summary['versions'])}."


def team_text(summary):
    lines = ["Team mirror", _subtitle(summary)]
    for k in NUMBER_KEYS:
        label, unit = LABELS[k]
        row = summary["numbers"][k]
        if row.get("too_few"):
            lines.append(f"{label}: too few cards for this number ({row['n']} of 5 needed).")
        else:
            lines.append(f"{label}: median {row['median']}{unit}, middle half {row['p25']}–{row['p75']}{unit} (from {row['n']} cards)")
    return "\n".join(lines + [""] + TEAM_CANNOT + ["Ranges only: Mirror never shows the lowest or highest card, a rank, or who sent which card."])


def write_team_page(summary, out_html: Path):
    cards = []
    for k in NUMBER_KEYS:
        label, unit = LABELS[k]
        row = summary["numbers"][k]
        content = f"<section class='card'><h2>{html.escape(label)}</h2>"
        if row.get("too_few"):
            content += f"<p>Too few cards for this number ({row['n']} of 5 needed).</p>"
        else:
            scale = 100 if k.endswith("_pct") else max(1, math.ceil(row["p75"] * 1.5))
            left, width, tick = (100 * row["p25"] / scale, 100 * (row["p75"] - row["p25"]) / scale, 100 * row["median"] / scale)
            content += (f"<p class='value'>{html.escape(str(row['median']) + unit)}</p><p>median</p>"
                        f"<div class='bar' aria-hidden='true'><span class='band' style='left:{left:.2f}%;width:{width:.2f}%'></span>"
                        f"<span class='tick' style='left:{tick:.2f}%'></span></div>"
                        f"<p>middle half {row['p25']}–{row['p75']}{html.escape(unit)} (from {row['n']} cards)</p>")
        cards.append(content + "</section>")
    template = Path(__file__).with_name("team_template.html").read_text(encoding="utf-8")
    replacements = {"SUBTITLE": html.escape(_subtitle(summary)), "CARDS": "\n".join(cards),
                    "CANNOT": "".join(f"<li>{html.escape(line)}</li>" for line in TEAM_CANNOT),
                    "DISCLAIMER": html.escape(DISCLAIMER)}
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(template, encoding="utf-8")
    return out_html
