# Mirror threat model

Written for v0.1. It says who Mirror protects against, what each protection is, and what it does not cover. If a claim here is not backed by a test or a command you can run, treat it as a claim, not a guarantee.

## What is being protected

| Asset | How sensitive |
|---|---|
| **Your session logs** (Claude Code, Codex, Cursor) | High. They hold your messages, pasted secrets, client and colleague names, and other people's information. |
| **Numbers Mirror derives** (counts, percentages, active minutes) | Low. |
| **Your notes** (the optional answer to "does this match your day?") | Medium. They are your own words. |

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
| The HTML report cannot load anything from the internet | The report carries a strict content policy; test checks it and finds no external URLs |
| Works with the network switched off | On macOS: `sandbox-exec -p '(version 1)(allow default)(deny network*)' python3 mirror.py day --yes` |
| First-run consent, and full removal | `mirror.py forget`; test `test_forget` |

## What Mirror does not protect

- **Your logs stay on disk as the AI tools wrote them.** Mirror does not redact, move or delete them. Claude Code removes old sessions on its own schedule.
- **Text exists briefly in memory** while one line of a log is parsed and labelled. Files are read one line at a time, never loaded whole. A crash dump or swap file could still capture that instant.
- **Malware or another user with your rights** can read the logs without Mirror.
- **Windows is covered by automated tests, not by an OS-level network block.** The macOS command above is the only enforcement check we have; on Windows and Linux you rely on the code and the tests.
- **Labels are rough** (about 70% agreement on one person's messages). Do not use Mirror's output to judge a person, and do not let anyone else use it to judge you.
- **Cloud sync.** `~/Mirror` is deliberately outside Documents and Desktop, which iCloud and OneDrive often sync. If you have set up sync for your whole home folder, the reports will sync too.
- **The report page contains your notes** (it shows them back to you). Send the share card, not the report file.
- **The launchers are unsigned.** Your computer warns you the first time; that is expected and the only way to know they are unmodified is to compare with the GitHub repo.
- **The share card is your choice.** If you paste it into a chat or send it, whoever receives it sees those numbers.

## Consent changes when the reading changes

The first-run notice lists every folder Mirror reads. When Mirror started reading Cursor chats, the consent version went from 1 to 2, so everyone who had agreed before is asked again. Test `test_untimed_approval_is_not_counted_as_quick` and `test_no_text_kept` cover the Cursor reader.

## Rule for changing Mirror

Any change that adds a network library, reads a new file, stores message text, or prints something new to the chat must update this document and the tests in the same commit.
