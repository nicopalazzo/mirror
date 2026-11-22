# Mirror threat model

Written for v0.1. It says who Mirror protects against, what each protection is, and what it does not cover. If a claim here is not backed by a test or a command you can run, treat it as a claim, not a guarantee.

## What is being protected

| Asset | How sensitive |
|---|---|
| **Your session logs** (Claude Code, Codex, Cursor) | High. They hold your messages, pasted secrets, client and colleague names, and other people's information. |
| **Numbers Mirror derives** (counts, percentages, active minutes) | Low. |
| **Your notes** (the optional answer to "does this match your day?") and **markers** (`mirror.py mark`) | Medium. They are your own words. |
| **The numbers-only ledger** (`~/.mirror/days.jsonl`) | Low to medium. Numbers only, but a longer history of your habits (hours of the day, active minutes) than the logs keep. |

## Who Mirror is designed against

| Actor | What could go wrong | Protection |
|---|---|---|
| **The author or a later contributor** | The code starts sending data, or reads more than it should | No networking libraries or command-running calls are allowed in the source. A test scans every file and fails if one appears. |
| **Someone tampering with the copy you receive** | A modified Mirror reads or sends more | The code is short and readable (start with `mirror_core/readers.py`). Compare against the GitHub repo. |
| **Your AI provider**, when you run Mirror through the `mirror` skill | It sees what Mirror prints in the chat | Mirror prints numbers and questions only, never your messages. The skill asks your permission first and offers a terminal alternative. |
| **Other apps or people on the computer** | They read what Mirror stored | Mirror stores numbers and your notes in `~/.mirror`, and report pages in `~/Mirror`. `forget` deletes both (only Mirror's own `mirror-*.html` files in `~/Mirror`). Malware that already has your user rights could read your logs directly, so Mirror adds little to that risk. |
| **Whoever you share numbers with** | Numbers identify you or reveal habits | The share card holds numbers only, notes are excluded unless you add `--include-note`, and Mirror sends nothing by itself. Sending is your decision. |
| **Your employer or a client** | Your logs contain their confidential information | Mirror reads logs locally and keeps no message text. Check your employer's rules before running it on a work computer. |

## The protections, and how to check each one

| Protection | How to verify |
|---|---|
| No networking or command-running code | `python3 -m unittest discover -s tests -v`, test `test_no_network_or_exec_code` |
| Opens only session files (`*.jsonl`), never credentials, settings, MCP configuration, canvases or Cursor subagent transcripts | Same suite, test `test_only_session_files_are_opened`, which plants decoy files |
| **Message text is dropped as soon as it is read.** Each message is labelled by simple rules, then only its type and length are kept. Project folders and paths become short hashes. | Test `test_readers_return_no_message_text_or_paths` |
| Reports and share cards contain no message text | Tests `test_report_is_offline_and_has_no_prompt_text`, `test_share_card_has_numbers_only` |
| The double-click launchers (`Mirror.command`, `Mirror.bat`) only run `mirror.py` and fetch nothing | Test `test_launchers_exist_and_do_not_fetch_anything`; CI also runs each launcher on Windows, macOS and Linux |
| The HTML report cannot load anything from the internet | The report carries a strict content policy; a test checks it and allows one external URL only: the feedback link in the footer, a plain link that opens only if the reader clicks it |
| Works with the network switched off | On macOS: `sandbox-exec -p '(version 1)(allow default)(deny network*)' python3 mirror.py day --yes` |
| First-run consent, and full removal | `mirror.py forget`; test `test_forget` |
| The ledger holds an allowlist of count fields only: no message text, no project hashes, no session ids, no model names | Test `test_ledger_holds_numbers_only` |
| Days still in the logs are recomputed; the ledger only fills days the logs lost, and says which rules counted them | Tests `test_days_still_in_the_logs_are_recomputed`, `test_ledger_keeps_days_the_logs_lost` |
| Markers are shown back in your report but never in the share card | Test `test_markers_never_in_share_card` |
| `forget` deletes the ledger and the markers | Test `test_forget_deletes_ledger_and_markers` |
| `ledger off` stops writing and reading the ledger (reports use log days only); `ledger forget` deletes that file only | Test `test_ledger_off_stops_reading_and_writing_and_forget_deletes_only_it` |

## The weekly guess (`mirror_core/guess.py`)

`report` asks one question in the terminal at the start of a new week, before it builds the page. It reads nothing new: the count comes from the same labelled numbers as the rest of the report.

| Protection | How to verify |
|---|---|
| `~/.mirror/guess.json` holds a setting and, per week, the week, your guess and the count: numbers only, never message text. A skip stores the week alone | Tests `test_state_holds_two_numbers_per_week_and_no_text`, `test_enter_skips_silently_and_is_not_asked_again_that_week` |
| Asked only in a terminal, at most once a week, never on the same open as the first-run quiz. Runs without a terminal (`/mirror:report`, launchers in test mode) ask nothing and store nothing | Tests `test_asks_once_a_week_and_the_page_shows_the_gap`, `test_never_on_the_same_open_as_the_first_run_quiz`, `test_not_asked_without_a_terminal_and_nothing_stored` |
| `mirror.py guess off` stops it; `forget` deletes the file with the rest of `~/.mirror` | Test `test_guess_off_stops_the_question_and_forget_deletes_it` |
| The report shows the gap and past gaps, with no score, streak or verdict | Test `test_no_score_streak_or_verdict_in_the_words` |

The report page now contains your past guesses next to the counts. Like your notes, they are yours: send the share card (which does not include them), not the report file.

## The nudge plugin (Claude Code)

| Protection | How to verify |
|---|---|
| The hook reads only the prompt Claude Code passes it and Mirror's own files in `~/.mirror`; it opens no log file | `mirror_core/nudge.py`, function `on_prompt` |
| The prompt is labelled and dropped; `~/.mirror/nudge.json` holds counts, times, session ids, settings and a 0/1 flag per recent message (question or pushback, or not) only | Test `test_state_holds_no_prompt_text` |
| Off until you type `/mirror:on`; `/mirror:off` stops it | Tests `test_off_by_default_intro_once`, `test_off_stops_everything` |
| Claude cannot turn nudges on or off, snooze or start a check by itself | Every plugin skill sets `disable-model-invocation: true`; test `test_manifest_hook_and_skills` |
| The nudge line is shown to you as a `systemMessage`; the hook runs synchronously because an async hook's message goes to Claude instead | Same test checks the hook is not async |
| A broken hook never blocks your prompt | Test `test_hook_never_raises`; 5-second timeout in `hooks.json` |
| Backs off when ignored, and steps back for a day after 3 ignored nudges | Test `test_ignored_nudges_back_off_then_step_back` |
| The band handover (0.4.1) reads one more file, `~/.mirror/band.json`, and only when a nudge fires. Mirror never writes it: a band above the prompt does, with session ids and times only. With a heartbeat under 60 seconds old for this session, the nudge still holds the message, but the chat shows a short pointer to the band. A missing, stale, broken or other-session file gives the full nudge. No message text is read from or written to it | `mirror_core/nudge.py`, function `band_present`; test `test_band_present_shortens_the_reason_but_still_blocks` |

The welcome-back line (`mirror_core/welcome.py`, called from the same hook) adds these:

| Protection | How to verify |
|---|---|
| It reads only the clock and the prompt the hook receives; `~/.mirror/welcome.json` holds times, counts and settings, never message text | Test `test_state_holds_no_prompt_text` (welcome) |
| Off until you type `/mirror:on`; `/mirror:off` stops it, `/mirror:snooze` pauses it | Tests `test_off_by_default`, `test_snooze_and_off`, `test_nudge_on_and_off_drive_the_welcome` |
| It never opens the report for you and holds your message once; Enter sends it unchanged | Test `test_offers_first_prompt_of_a_new_week_once`; the line only names the `/mirror:report` command |
| At most one offer a week; 3 skipped offers pause it for 30 days | Tests `test_long_gap_inside_a_week_does_not_offer_twice`, `test_three_skips_in_a_row_pause_for_a_month` |
| A fault in it never stops the nudge or your prompt | `hook_main` catches errors around it; test `test_hook_never_raises` |

The evening limit (`mirror_core/limit.py`, 0.5.0, called from the same hook after the welcome-back line) adds these:

| Protection | How to verify |
|---|---|
| It reads only the clock and the prompt the hook receives; `~/.mirror/limit.json` holds the time you set, dates, clock times and one word per evening (carried on, stopped, no message after it), never message text | Test `test_state_holds_no_prompt_text` (EveningLimit) |
| Off until you set a time yourself (`mirror.py limit set 19:00` or `/mirror:limit`); `/mirror:off` turns it off, and `/mirror:on` brings it back only if you had set one | Tests `test_off_by_default_and_parse`, `test_mirror_off_and_on_drive_the_limit`; both skills set `disable-model-invocation: true` |
| It holds one message per evening and never stops you: Enter sends it unchanged, and `/mirror:stop` only records that you stopped | Tests `test_holds_once_past_the_limit_then_carried_on`, `test_stop_and_left_are_recorded` |
| A fault in it never stops the nudge or your prompt | `hook_main` catches errors around it; test `test_hook_blocks_with_the_limit_line` |
| `/mirror:limit` asks Claude to run `mirror.py limit set HH:MM` with the time you typed; Claude converts it, so check the line it runs | Read `plugins/mirror-claude/skills/limit/SKILL.md` |

Not verified yet: whether Claude also sees the `systemMessage` line (the docs say it is shown to the user and do not say it is added to context). Check in a live session before relying on it.

A hook runs with your user rights outside Claude Code's sandbox, on every prompt. Installing from a marketplace added as a **local folder** runs the files in that folder as they are; installing from the GitHub marketplace runs a cached, versioned copy that only changes when you update.

## Session drift (unreleased)

How your messages change by minutes into a working stretch (a stretch is one session with no gap over 30 minutes) and by hour of day. It is shown in `week` and in the report. It reads no new file and no new field: it uses the time, label and length that Mirror already keeps for each message. What is new is that message length is now printed, as a median.

| Protection | How to verify |
|---|---|
| Only pooled counts are printed: messages, how many asked or pushed back, the median length in characters, and quick approvals, per part of a stretch and per hour. Never message text, project names or paths | Test `test_drift_week_and_report_have_no_message_text` |
| A part or hour with fewer than 5 messages shows no share and no median, so a single message's length is not shown on its own | Test `test_drift_hides_cells_with_fewer_than_5` |
| Nothing new is stored: the numbers are worked out from the logs each time and live only in the printed text and the report page | `mirror_core/drift.py` writes no file; `mirror.py` passes the result straight to `week_text` and `render_html.build` |
| No score, no threshold, no advice; the `explain drift` entry carries a "cannot tell" line and no practice | Test `test_explain_drift_reveals_only` |

## What Mirror does not protect

- **Your logs stay on disk as the AI tools wrote them.** Mirror does not redact, move or delete them. Claude Code removes old sessions on its own schedule.
- **Text exists briefly in memory** while one line of a log is parsed and labelled. Files are read one line at a time, never loaded whole. A crash dump or swap file could still capture that instant.
- **Malware or another user with your rights** can read the logs without Mirror.
- **Windows is covered by automated tests, not by an OS-level network block.** The macOS command above is the only enforcement check we have; on Windows and Linux you rely on the code and the tests.
- **Labels are rough** (about 70% agreement on one person's messages). Do not use Mirror's output to judge a person, and do not let anyone else use it to judge you.
- **Cloud sync.** `~/Mirror` is deliberately outside Documents and Desktop, which iCloud and OneDrive often sync. If you have set up sync for your whole home folder, the reports will sync too.
- **The report page contains your notes and markers** (it shows them back to you). Send the share card, not the report file.
- **The launchers are unsigned.** Your computer warns you the first time; that is expected and the only way to know they are unmodified is to compare with the GitHub repo.
- **The share card is your choice.** If you paste it into a chat or send it, whoever receives it sees those numbers.

## Consent changes when the reading changes

The first-run notice lists every folder Mirror reads. When Mirror started reading Cursor chats, the consent version went from 1 to 2, so everyone who had agreed before is asked again. Test `test_untimed_approval_is_not_counted_as_quick` and `test_no_text_kept` cover the Cursor reader.

## The ledger and markers (stored, not read)

The ledger (`~/.mirror/days.jsonl`) and markers (`~/.mirror/marks.jsonl`) add two stored files and no new reading. The consent version stays at 2, for three reasons: the consent rule is tied to what Mirror reads, and that is unchanged; both files sit in `~/.mirror`, the folder the notice already names; and the ledger holds the same per-day numbers every report page already stores in `~/Mirror`. The notice now names both, and Mirror prints one line the first time it creates the ledger, so people who agreed before are told too.

What it does not cover:
- **A longer history on disk.** Before, Claude Code's cleanup limited how far back anyone with access to your account could see your habits. The ledger keeps every day Mirror has counted until you run `forget` or `ledger forget`. `ledger off` stops it growing but keeps the file. Deleting a session from a tool's logs does not remove its day from the ledger.
- **Markers are free text.** Mirror cannot stop you from typing a name or a secret into one. They stay on this computer and out of the share card, but they appear in your report page.

## Rule for changing Mirror

Any change that adds a network library, reads a new file, stores message text, or prints something new to the chat must update this document and the tests in the same commit.
