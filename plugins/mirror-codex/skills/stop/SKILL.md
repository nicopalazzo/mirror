---
name: stop
description: Note that the user stopped at their evening limit. Run only when the user explicitly invokes it ($mirror:stop).
---

Run this command from the plugin folder (two levels above this file, where `mirror.py` lives) and read its output:

```bash
python3 mirror.py limit stop
```

Tell the user the line printed above in one sentence. Nothing else: no summary of the session, no next steps.
