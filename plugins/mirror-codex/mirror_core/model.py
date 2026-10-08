from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Turn:
    """One message from the human."""
    ts: datetime
    tool: str
    session: str
    project: str
    kind: str = ""
    chars: int = 0
    # There is deliberately no text field: a message is labelled the moment it is read, then dropped.


@dataclass
class Action:
    """One thing an AI did: a reply or a tool call."""
    ts: datetime
    tool: str
    session: str
    project: str
    actor: str
    cat: str  # reply, read, research, write, shell
    timed: bool = True  # False when the log carries no time for this action (Cursor replies)


CATEGORIES = ["reply", "read", "research", "write", "shell"]
