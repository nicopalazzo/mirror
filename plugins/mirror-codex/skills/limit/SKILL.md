---
name: limit
description: Set, show or turn off Mirror's evening limit, a time to stop working with AI. Run only when the user explicitly invokes it ($mirror:limit).
---

Run this command from the plugin folder (two levels above this file, where `mirror.py` lives) and read its output:

```bash
python3 mirror.py limit status
```

- If the user named a time with the command (for example 19:00, 19h, 7pm), convert it to the 24-hour clock (HH:MM) and run exactly `python3 mirror.py limit set HH:MM` from the same folder, with nothing else on the line.
- If they said off, run `python3 mirror.py limit off`.
- If they gave nothing, show the status lines as they are.

Then tell the user Mirror's line in one sentence. Do not suggest a time, and add no advice about how long or how late to work.
