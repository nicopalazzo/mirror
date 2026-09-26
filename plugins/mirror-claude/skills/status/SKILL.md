---
name: status
description: Show whether Mirror nudges are on, and how the user has answered them. Run only when the user types /mirror:status.
disable-model-invocation: true
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" nudge status`

Show the user the lines above as they are. Add no interpretation or advice.
