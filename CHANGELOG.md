# Changelog

All notable changes to Mirror. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

The command-line tool (`mirror_core.__version__`) and the Claude Code plugin (`plugin.json`) carry separate versions.

## [Unreleased]

Plugin version 0.3.1.

### Added

- One-time "look in the mirror" quiz: on a new install, the first report opens with four guesses (pushback, plain "ok", AI actions per message, quick approvals), then shows each guess next to what Mirror counted, as a gap. The answers live in the page only; Mirror stores one word (`pending`, `shown` or `skipped`) in `~/.mirror/config.json`. Until then `day` and `week` hold the numbers back; `--skip-quiz` skips it. Not shown to existing installs or when there are fewer than 30 messages.
- `/mirror:report` in the Claude Code plugin: builds the HTML report from your own logs and opens it in the browser. It never accepts the first-run notice for you.
- Codex plugin (`plugins/mirror-codex`, marketplace at `.agents/plugins/marketplace.json`): the same nudge hook and five skills, with copy that says `$mirror:` and "the last answer" inside Codex. Not yet tested inside a live Codex session.
- Contributing guide with privacy rules, pull request template and gitleaks pre-commit hook.
- A message sent right after a nudge counts as its answer: a question or pushback means acted, another non-approval means edited, and a plain approval means sent anyway. Only "sent anyway" counts as ignored.
- Ratio rule for the nudge (`mirror.py nudge rule ratio`): fires when a share of your last messages (20 by default) had no question or pushback, so one question no longer resets everything. The streak rule stays the default.
- Hold-back test (`mirror.py nudge holdback 0.5`): when the rule fires, a coin decides whether the nudge is shown or silently held back. `/mirror:status` compares the acted rate in both. Held-back moments never count as ignored. Off by default.
- Copy test (`mirror.py nudge action-copy 0.5`): that share of shown nudges asks you to add one line (what the answer changes, or one question) instead of "Review Claude's last answer?". Nothing is enforced; Enter still sends. `/mirror:status` compares both copies. Off by default.
- `echo` skill in the Claude Code plugin: when nudges are on, Claude ends a proposal for a hard-to-reverse step with a request to answer with a detail from the plan (a file name, a branch), so approving takes a read. Claude decides when it applies, so how often it loads is untested. Not in the Codex plugin yet.
- Quick approvals by weekday and hour: each day now keeps how many approvals after file changes came in each hour and how many were quick (`hours_approvals`, `hours_quick`; counts only). The report heatmap has a "Quick approvals" view of it; cells with fewer than 5 timed approvals stay grey.
- Nudge settings from the command line: `holdback`, `rule`, `ratio-threshold`, `window`, `threshold`, `cooldown`.
- `scripts/calibrate_nudge.py`: replays your own Claude Code messages through each rule and prints how often it would fire. Read-only, counts only.

### Changed

- The report is mobile first: 44 px tap targets, text of 14 px or more, every table in a scroll wrapper, tap-to-read chart marks with a readout line, 3-hour bins in the weekday-by-hour heatmap and 12 weeks in the calendar on a phone, compact tiles, and the supporting charts behind "More charts". Design rules for contributors are in `CONTRIBUTING.md`.
- Nudge copy says what happened, then one action, then the controls.
- The HTML report is now a dashboard: a "What changed" block, four index tiles with sparklines, a weekly chart with your usual range, and four supporting charts, each with a table view. "Usual" comes from your first 12 weeks (average plus or minus 2.66 times the average week-to-week change); a point outside it, or 8 weeks in a row on one side, counts as a signal. With fewer than 6 weeks of data it compares with last week instead. The 7/14/30-day selector is gone; the report shows the last 26 weeks.

### Fixed

- "ok, but…" and "not ok" are read as pushback. Three real demo prompts were mislabelled before.

## [0.1.0] - 2026-09-26

First version: a local, read-only look at how you work with AI. Plugin version 0.2.0. The nudge shows its line by blocking that one prompt, because Claude Code does not display hook system messages.

### Added

- `day`, `week`, `report`, `sources`, `explain`, `share-card`, `doctor`, `feedback` and `forget` commands.
- Readers for Claude Code, Codex and Cursor session logs. Message text is dropped as it is read.
- Offline HTML report saved in `~/Mirror`, with a numbers-only share card.
- Double-click launchers for macOS and Windows.
- Threat model and a skill for Claude Code and Codex.
- Claude Code plugin with an optional nudge the user switches on.
