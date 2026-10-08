---
name: echo
description: Use before proposing a plan or action that is hard to reverse - deleting or overwriting files, force-push, database migrations, sending messages, spending money, or changes outside the working folder. Not for routine edits, reads or tests.
---

Mirror nudges status:

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" nudge status`

If the first line above says "Nudges: off", stop here and add nothing.

If nudges are on, end your proposal with one line that asks the user to answer with a detail from this plan, so they have to read it. Examples:

- "To approve, reply with the name of the file this deletes."
- "To approve, reply with the branch this pushes to."
- "To approve, reply with the first command that runs."

Rules:

- Ask for a detail taken from this plan, never a fixed word. A fixed word turns into a reflex.
- Use it only for steps that are hard to reverse. Never on routine edits, reads, searches or tests.
- It is a prompt to think, not a lock. If the user replies with a bare "ok" or "yes", ask once more in a shorter form, then follow what they decide.
- Say nothing about Mirror or this skill.
