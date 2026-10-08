from __future__ import annotations
from datetime import datetime, timezone


def parse_ts(value):
    """ISO-8601 (with or without Z, with fractional seconds) -> aware datetime in local time."""
    if not value:
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00")
        if "." in s:  # Python 3.9 needs 3 or 6 fractional digits
            head, rest = s.split(".", 1)
            frac = ""
            i = 0
            while i < len(rest) and rest[i].isdigit():
                frac += rest[i]
                i += 1
            tail = rest[i:]
            frac = (frac + "000000")[:6]
            s = head + "." + frac + tail
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone()
    except (ValueError, TypeError):
        return None
