# Mirror for Claude Code

Built from the repository root by `python3 scripts/build_plugins.py`. Do not edit `mirror.py` or `mirror_core/` here; edit the root copies and rebuild.

What it adds:
- One hook (`UserPromptSubmit`) that counts your messages and, only if you turn nudges on, shows you one line after a long run without a question or pushback. It reads only the prompt Claude Code hands it, stores counts and times in `~/.mirror/nudge.json`, and never stores your text or uses the network.
- Commands: `/mirror:on`, `/mirror:off`, `/mirror:snooze`, `/mirror:check`, `/mirror:status`, `/mirror:report`. Claude cannot run them on its own. `/mirror:report` builds the HTML report from your own logs and opens it in your browser; it does not accept the first-run notice for you, so run `python3 mirror.py report` once in a terminal first.
- Skill `echo` (not a command): when nudges are on, Claude may end a proposal for a hard-to-reverse step by asking you to reply with a detail from the plan, such as a file name. It does nothing while nudges are off.
