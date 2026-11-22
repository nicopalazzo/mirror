# Changelog

All notable changes to Mirror. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

From 0.3.1 the command-line tool (`mirror_core.__version__`) and both plugins (`plugin.json`) carry the same version.

## [Unreleased]

### Added

- Reply time against change size: a report card that groups each run of AI file changes (no message from you in between) by lines changed (under 20, 20 to 200, over 200) and shows, per group, the median time the AI kept working, the median time to your next message, and the share of quick agreements. Groups with fewer than 5 runs are not shown. Claude Code and Codex only; Cursor's log has no reply times. `mirror.py explain size` says what it can and cannot tell you. No threshold and no advice.
- The readers now count the lines in each file change (Claude Code `Write`, `Edit`, `MultiEdit`, `NotebookEdit`; Codex `apply_patch`) and keep only that number; the code is dropped at once, like message text. `THREAT-MODEL.md` updated.
- Numbers-only ledger: each run of `day`, `week`, `report` or `feedback` saves each day's numbers to `~/.mirror/days.jsonl` (respects `MIRROR_HOME`), with the labelling-rules version (`RULES_VERSION` in `classify.py`) and the quick-approval line each day was counted with. Days still in the logs are recomputed; days the logs no longer hold come from the ledger, so the 26-week chart survives Claude Code's 30-day cleanup. When the logs hold less for a day than the ledger already counted, the fuller day is kept. Only an allowlist of count fields is written; no message text, project hashes or session ids. Mirror says so once when it creates the file; the first-run notice and `sources` list it; `forget` deletes it. The report says how many days come from the ledger, and how many were counted with other rules.
- Markers: `mirror.py mark "<your words>"` (today, or `--day YYYY-MM-DD`), `mark list`, `mark remove N`, stored in `~/.mirror/marks.jsonl`. The report shows the four numbers in the 4 weeks before each marker next to the 4 weeks from it, with your usual weekly range, and the line "Before and after is not cause and effect: many things change at once." No verdict. Markers are never in the share card. `explain marks` gives its "cannot tell you".
- `mirror.py ledger off|on|status|forget`: off stops writing and reading `days.jsonl` (reports fall back to the days the logs still hold) and keeps the file; the setting is `"ledger": "off"` in `config.json`. `ledger forget` deletes `days.jsonl` only; `forget` still deletes everything.
- No consent version bump: Mirror reads nothing new, and both files sit in the folder the first-run notice already names. See `THREAT-MODEL.md`.
- Guess first, every week: the first `report` of a new calendar week, run in a terminal, asks one question before the page is built: "What share of your messages last week were a question or pushback?" The report then opens with your guess next to what Mirror counted for last week (Monday to Sunday), as a gap in points, with one question to ask yourself. Enter skips, silently, and the week is not asked again. Never on the same open as the first-run quiz, and only when last week has at least 10 messages. Not asked from `/mirror:report` or any other run without a terminal.
- `~/.mirror/guess.json` keeps one entry per week: the guess and the count (two numbers), or the week alone when skipped. A "My weekly guesses" table in the report lists past weeks with their gap. No streaks, scores, badges or "right/wrong". `mirror.py guess off` stops the question, `guess on` brings it back, `guess status` shows the setting; `forget` deletes the file.
- The question is asked in the terminal, not the page, because the page is a static file that cannot save anything to `~/.mirror` without network code.
- Session drift: how your messages change over a working stretch. A stretch is your messages in one session with no gap over 30 minutes. For the first 30 minutes, 30 to 60, 60 to 120 and after 120, and for each hour of the day, Mirror shows how many messages asked a question or pushed back, the median message length in characters, and quick approvals after file changes. Counts are added up first, then each share is worked out; a part with fewer than 5 messages is hidden. It appears as a section in `week` (this week's days) and as a fold-out table in the report (everything loaded), with a switch between minutes into a stretch and hour of day. `mirror.py explain drift` says what it cannot tell you: fewer questions late can mean the task got clear. No score, no limit, no advice. Message length was already kept; this is the first number that prints it. Tested on synthetic logs only.

## [0.5.0] - 2026-11-22

Command-line tool and both plugins (Claude Code and Codex) at 0.5.0.

### Added

- Time with AI: the report has a "Time with AI" card for the last 7 days (active time, first and last activity per day, days with activity between midnight and 05:00). `week` adds first and last columns and the same facts. Built from data Mirror already had; covers Claude Code, Codex and Cursor.
- Evening limit: `mirror.py limit set 19:00` (or `/mirror:limit 19:00`, `$mirror:limit` in Codex) sets a time to stop working with AI. Off by default. The first message after that time is held once with "It's 19:12. You set 19:00 as the time to stop working with AI." Enter sends it; `/mirror:stop` records that you stopped. An evening runs until 05:00. Mirror notes one word per evening (carried on, stopped, no message after it) in `~/.mirror/limit.json`, and the report, `day` and `week` show it back. It never stops you. `/mirror:off` turns it off with the nudge and the welcome line.
- Not yet tested in a live Claude Code or Codex session.

## [0.4.1] - 2026-10-24

Command-line tool and both plugins (Claude Code and Codex) at 0.4.1.

### Added

- Band handover: when the mod-area band (a Claude Code mod that draws above the prompt) is running in the same session, it writes a heartbeat to `~/.mirror/band.json` (session id and time only). While that heartbeat is under 60 seconds old, a nudge still holds the message, but the chat shows one short line, "Mirror is holding this message: answer in the band above ↑", and the band shows the nudge with its buttons (Check it, Snooze, Dismiss, Send anyway, Turn off Mirror). Without the band, or with a stale heartbeat, the nudge is unchanged. Codex never writes the heartbeat, so its behaviour is unchanged. Not yet tested in a live session.

## [0.4.0] - 2026-10-23

Command-line tool and both plugins (Claude Code and Codex) at 0.4.0.

### Added

- Welcome-back line: after a break, the first message of a new week (or after 3 days away, at most once a week) is held once with "Welcome back. Take a quick look in the Mirror? Last week is ready." Enter sends your message unchanged; `/mirror:report` opens the report. Mirror never opens it for you, and Claude never sees the line. Off until you type `/mirror:on`, which now turns on the nudge and the welcome together; `/mirror:off` stops both and `/mirror:snooze` pauses both. State is counts and times only, in `~/.mirror/welcome.json`.
- It logs only whether each offer led to a report (opened), was carried past (skipped), snoozed or switched off. After 3 skipped offers in a row it pauses for 30 days and says so once. No streaks, badges or "you missed a week" copy.
- `mirror.py welcome` (`on`, `off`, `status`, `when start-of-week|start-of-day`, `gap-days`, `holdback`): `status` shows the counts; `holdback 0.5` silently holds back that share of offers, for a comparison like the nudge's. Off by default.
- Design and test plan: `research/MIRROR-WELCOME-BACK-DRAFT.md`. Not yet tested in a live Claude Code or Codex session.
- A "Tell me what happened" feedback link in the report footer, to a short optional form. It is a plain link that opens only if you click it; Mirror still sends nothing, and the report still loads nothing from the internet. The report test now allows that one URL and no other.

## [0.3.1] - 2026-10-09

Command-line tool and both plugins (Claude Code and Codex) at 0.3.1.

### Added

- One-time "look in the mirror" quiz: on a new install, the first report opens with four guesses (pushback, plain "ok", AI actions per message, quick approvals), then shows each guess next to what Mirror counted, as a gap. The answers live in the page only; Mirror stores one word (`pending`, `shown` or `skipped`) in `~/.mirror/config.json`. Until then `day` and `week` hold the numbers back; `--skip-quiz` skips it. Not shown to existing installs or when there are fewer than 30 messages.
- `/mirror:report` in the Claude Code plugin: builds the HTML report from your own logs and opens it in the browser. It never accepts the first-run notice for you.
- Codex plugin (`plugins/mirror-codex`, marketplace at `.agents/plugins/marketplace.json`): the same nudge hook and five skills, with copy that says `$mirror:` and "the last answer" inside Codex. Not yet tested inside a live Codex session.
- `$mirror:report` in the Codex plugin (version 0.3.1): builds the HTML report and opens it, with the first-run quiz on a new install. It never accepts the first-run agreement for the user. Codex's sandbox can block writing `~/Mirror`: the skill then asks the user for approval to re-run the same command outside the sandbox, and falls back to a terminal instruction if they decline. Not yet tested in a live Codex session.
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
