---
name: stop
description: Note that the user stopped at their evening limit. Run only when the user types /mirror:stop.
disable-model-invocation: true
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" limit stop`

Tell the user the line above in one sentence. Nothing else: no summary of the session, no next steps.
