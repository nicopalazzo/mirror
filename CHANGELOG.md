# Changelog

All notable changes to Mirror. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

The command-line tool (`mirror_core.__version__`) and the Claude Code plugin (`plugin.json`) carry separate versions.

## [Unreleased]

Plugin version 0.3.0.

### Added

- `/mirror:report` in the Claude Code plugin: builds the HTML report from your own logs and opens it in the browser. It never accepts the first-run notice for you.
- Contributing guide with privacy rules, pull request template and gitleaks pre-commit hook.
- A message sent right after a nudge counts as its answer: a question or pushback means acted, another non-approval means edited, and a plain approval means sent anyway. Only "sent anyway" counts as ignored.
- Ratio rule for the nudge (`mirror.py nudge rule ratio`): fires when a share of your last messages (20 by default) had no question or pushback, so one question no longer resets everything. The streak rule stays the default.
- Hold-back test (`mirror.py nudge holdback 0.5`): when the rule fires, a coin decides whether the nudge is shown or silently held back. `/mirror:status` compares the acted rate in both. Held-back moments never count as ignored. Off by default.
- Nudge settings from the command line: `holdback`, `rule`, `ratio-threshold`, `window`, `threshold`, `cooldown`.
- `scripts/calibrate_nudge.py`: replays your own Claude Code messages through each rule and prints how often it would fire. Read-only, counts only.

### Changed

- Nudge copy says what happened, then one action, then the controls.

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
