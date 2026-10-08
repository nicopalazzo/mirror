---
name: report
description: Build Mirror's HTML report from the user's own logs and open it in the browser. Run only when the user types /mirror:report.
disable-model-invocation: true
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" report --open`

Tell the user in one sentence where the report was saved, and that the page shows their own notes, so they should not share their screen with it open. If the output says Mirror cannot ask for the first-run agreement, tell them to run `python3 mirror.py report` once in a terminal and answer y, then try again. Nothing else.
