---
name: check
description: Mirror's 2-minute pre-flight check on an AI answer the user is about to rely on. Run only when the user types /mirror:check.
disable-model-invocation: true
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/mirror.py" nudge check`

The user chose to check the last substantial answer you gave before relying on it. Do this, briefly:

1. Name in one line which output they are checking (your most recent substantial answer). If it is unclear, ask which one.
2. Post this template in one copyable code block, exactly as written, with no example answers:

```text
**Output checked** (what):
1. **Source** (do I know where it comes from?):
2. **One number** (did I check the one I'd repeat?):
3. **Frontier** (safe or risky for AI?):
4. **Agreement** (did it just agree with me?):
5. **Explain** (could I say it in my own words?):
```

3. Wait for their answers. Then, for any check they flagged, help them resolve it: give the source, suggest how to verify the one number, or give the strongest case against your own answer. Do not defend your answer before they have finished.
4. Keep it short. No lecture about AI use. If they say "skip", stop at once.
