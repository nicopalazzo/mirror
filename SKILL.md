---
name: mirror
description: Use when the user asks how their day, week or habits with AI went, mentions Mirror, or types /mirror. Runs the local Mirror tool, which counts patterns in the user's own Claude Code and Codex session logs and shows four numbers as reflection questions. Read-only, numbers only, nothing is sent anywhere.
---

# Mirror (skill)

Mirror is a small Python tool in this folder. It reads the user's own AI session logs (Claude Code, Codex, Cursor) on their computer and reports four numbers as questions to ask themselves. It is an exploration, not a test, a score or a diagnosis.

Run it from this skill's folder with `python3 mirror.py ...` (on Windows `py mirror.py ...`). If Python is missing, tell the user to install Python 3.8 or newer from python.org and stop.

## Before the first run: tell the user and get a yes

Say, in the user's language:

> Mirror reads your Claude Code, Codex and Cursor session logs on this computer. Whatever it prints will appear in this chat, so your AI provider will see those numbers, never your messages. Is that OK? If you would rather keep it fully local, I will give you the commands to run yourself in a terminal instead.

- If they prefer the terminal: give them `python3 mirror.py day` (Windows: `py mirror.py day`) and stop.
- If yes: run `python3 mirror.py sources`, show the output, and ask whether Mirror may read those folders. Only after a clear yes use `--yes` on later commands.

## The only commands you may run

| Purpose | Command |
|---|---|
| What Mirror can see (counts files, opens none) | `mirror.py sources` |
| Today, or another day | `mirror.py day --yes --no-feedback` (add `--day YYYY-MM-DD` or `--yesterday`) |
| Last 7 days | `mirror.py week --yes` |
| What a number means | `mirror.py explain challenge` (or `approval`, `delegation`, `focus`) |
| Record whether the numbers matched | `mirror.py feedback --yes --match yes|no|partly --note "..."` |
| Numbers to send, if the user chooses | `mirror.py share-card` |
| Something looks wrong | `mirror.py doctor --yes` |
| Delete everything Mirror stored | `mirror.py forget` |

## Hard rules

- Never open, read, list, search or copy anything in `~/.claude`, `~/.codex` or `~/.mirror` yourself. Only Mirror reads those, through the commands above.
- Never install anything, edit files, or send anything anywhere. Do not email, post or upload a share card; show it and let the user decide.
- Show Mirror's output as it is. Do not add scores, verdicts, "good" or "bad", or advice beyond Mirror's own questions. Say once that the message labels come from simple rules and are sometimes wrong.
- Never say you ran a command you did not run.

## After `day`

Ask: "Does this match how your day felt? Yes, no or partly, and anything the numbers missed?" Then record it with `feedback`. Ask before saving their note; it is their words and stays on their computer.

## Language

Reply in the user's language (English or French).
