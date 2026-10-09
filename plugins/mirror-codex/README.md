# Mirror for Codex

Built from the repository root by `python3 scripts/build_plugins.py`. Do not edit `mirror.py` or `mirror_core/` here; edit the root copies and rebuild.

What it adds:
- One hook (`UserPromptSubmit`) that counts your messages and, only if you turn nudges on, shows you one line after a long run without a question or pushback. It reads only the prompt Codex hands it, stores counts and times in `~/.mirror/nudge.json`, and never stores your text or uses the network.
- Skills: `mirror:on`, `mirror:off`, `mirror:snooze`, `mirror:check`, `mirror:status`, `mirror:report` (builds the HTML report and opens it; on a new install it opens with the one-time quiz). Codex only runs them when you invoke them.
