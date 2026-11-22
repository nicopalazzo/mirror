---
name: limit
description: Set, show or turn off Mirror's evening limit, a time to stop working with AI. Run only when the user types /mirror:limit.
disable-model-invocation: true
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" limit status`

The user typed /mirror:limit, followed by: $ARGUMENTS

- If they named a time (for example 19:00, 19h, 7pm), convert it to the 24-hour clock (HH:MM) and run exactly `python3 "<path>" limit set HH:MM`, where `<path>` is the file named on the "Mirror is at:" line above. Nothing else on the line.
- If they said off, run `python3 "<path>" limit off`, with the same path.
- If they gave nothing, show the status lines above as they are.

Then tell the user Mirror's line in one sentence. Do not suggest a time, and add no advice about how long or how late to work.
