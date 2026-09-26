# Mirror for Claude Code

Built from the repository root by `python3 scripts/build_plugins.py`. Do not edit `mirror.py` or `mirror_core/` here; edit the root copies and rebuild.

What it adds:
- One hook (`UserPromptSubmit`) that counts your messages and, only if you turn nudges on, shows you one line after a long run without a question or pushback. It reads only the prompt Claude Code hands it, stores counts and times in `~/.mirror/nudge.json`, and never stores your text or uses the network.
- Commands: `/mirror:on`, `/mirror:off`, `/mirror:snooze`, `/mirror:check`, `/mirror:status`. Claude cannot run them on its own.
