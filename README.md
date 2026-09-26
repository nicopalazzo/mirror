# Mirror

**A local, read-only look at how you work with AI.** Mirror reads your own Claude Code and Codex session logs on your computer and shows you how your day went: what you asked, when you pushed back, when you just said "ok", how much the AI did between your messages.

It is an **exploration**, not a test, a score or a diagnosis. The numbers are questions to ask yourself.

## Your data never leaves your computer

- **No network code.** Mirror imports no networking library. A test fails if one is added.
- **Nothing to install.** Python 3.8 or newer, standard library only. Mirror checks your version and tells you what to do if it is too old.
- **It opens session files only:** `~/.claude/projects/*/*.jsonl` and `~/.codex/sessions/**/rollout-*.jsonl` (plus `~/.codex/archived_sessions`). It never opens credentials, settings or databases in those folders. A test checks this against decoy files.
- **First run asks for permission** and lists exactly what it will read.
- **Your messages are not stored.** They are read in memory to count patterns. Reports and the share card contain numbers only, no prompt text.
- **It writes only to `~/.mirror`.** Delete everything with `mirror.py forget`.
- Reading the code takes ten minutes. Start with `mirror_core/readers.py`.

## Run it

You need Python 3.8+ (check with `python3 --version`, or `py --version` on Windows). Then, in the `mirror` folder:

| | macOS / Linux | Windows |
|---|---|---|
| How your day went | `python3 mirror.py day` | `py mirror.py day` |
| Last 7 days | `python3 mirror.py week` | `py mirror.py week` |
| HTML report (works offline) | `python3 mirror.py report --open` | `py mirror.py report --open` |
| What Mirror can see | `python3 mirror.py sources` | `py mirror.py sources` |
| What a number means | `python3 mirror.py explain challenge` | `py mirror.py explain challenge` |
| Numbers only, to share if you choose | `python3 mirror.py share-card` | `py mirror.py share-card` |
| Something looks wrong: versions and counts, no text | `python3 mirror.py doctor` | `py mirror.py doctor` |
| Delete everything Mirror stored | `python3 mirror.py forget` | `py mirror.py forget` |

If `py` is not found on Windows, try `python`. Use `--yes` after the command to accept the first-run notice without being asked.

## The four numbers

1. **Challenge rate:** how often you push back or ask a question, against how often you approve.
2. **Approvals:** share of short agreements, and how many came within 15 seconds of an AI turn that changed files.
3. **Delegation depth:** AI actions per message you sent, and the longest run of file changes without a message from you.
4. **Focus:** sessions, projects, tools and active minutes in the day.

Each has a plain "what it cannot tell you". Run `explain` to read it. Comparisons are always with **your own** earlier days, never with other people.

At the end of `day`, Mirror asks whether the numbers match how the day felt. That answer stays on your computer. `share-card` prints numbers only (add `--include-note` to add your notes), and Mirror sends nothing: you decide whether to pass it on.

## Limits, said plainly

- **Message labels are rules, not understanding.** They work in English and French and are wrong some of the time. On one person's 93 hand-labelled messages the rules agreed about 70% of the time (a small check, one labeller). Treat the split as rough.
- **Only tools whose logs Mirror can read are counted.** Web chats (claude.ai, chatgpt.com) leave no local log. Cursor is not read yet.
- **Claude Code deletes old sessions after about 30 days** unless you raise `cleanupPeriodDays` in its settings, so history is short.
- **"Quick approval" is an arbitrary 15-second line.** Change it with `--quick-seconds`.
- **Different Python or OS versions:** the code is checked for Python 3.8 syntax and the automated tests run on Python 3.8 to 3.13 on Mac, Linux and Windows. If a setup still fails, `doctor` prints what is needed to fix it, without any of your text.
- **Mac and Linux are tested here; Windows is covered by the automated tests in `.github/workflows/test.yml` but has not been tried by hand.** Tell us what breaks.

## Tests

```
python3 -m unittest discover -s tests -v
```

The tests use synthetic logs only (`tests/make_fixtures.py`). There are no real conversations in this repository.

## Status

Version 0.1, exploratory. Licence: MIT.
