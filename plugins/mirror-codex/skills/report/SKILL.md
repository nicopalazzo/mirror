---
name: report
description: Build Mirror's HTML report from the user's own logs and open it in the browser. Run only when the user explicitly invokes it ($mirror:report).
---

Run this command from the plugin folder (two levels above this file, where `mirror.py` lives) and read its output:

```bash
python3 mirror.py report --open
```

Tell the user in one sentence where the report was saved, and that the page shows their own notes, so they should not share their screen with it open. Do not open or read the report file yourself, and do not describe its contents.

- If the output says Mirror cannot ask for the first-run agreement, tell them to run `python3 mirror.py report` once in a terminal and answer y, then invoke `$mirror:report` again. Never add `--yes` yourself: the agreement is the user's decision.
- If the browser did not open, or the command could not write its folder because of the sandbox, tell them the saved path (or the error in one line) and to open the file from their own file manager.
- On a brand-new install the page opens with a one-time quiz before any numbers. If it is their first report, add one short sentence saying so. Nothing else.
