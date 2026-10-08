# Contributing

How changes land in Mirror. Written for me, for reviewers, and for the AI agents (Claude Code, Cursor) that pair on this repo.

## Privacy rules come first

These protect the promise in the README. A change that breaks one is not merged.

- **No network code.** Mirror imports no networking library, and a test fails if one is added.
- **Read session files only.** No credentials, settings, MCP configuration or databases. The decoy-file test checks this.
- **Keep no message text.** Label each message when it is read and keep only its type and length.
- **No real conversations in the repo.** Tests use the synthetic logs from `tests/make_fixtures.py`.
- **Standard library only, Python 3.8+.**
- If a change touches what Mirror reads or stores, update [THREAT-MODEL.md](THREAT-MODEL.md) in the same PR.

## Design rules: mobile first

Every page a person opens (the quiz, the reveal, the report dashboard, the details tables) is designed for a phone first. Check each one, not only the screen you just built.

- **Write the phone layout as the base** and widen it with `min-width` media queries. Never shrink a desktop layout with `max-width` patches.
- **Check at 375 px wide** before you call a page done: no sideways scroll on the page, nothing cut off.
- **Tap targets are at least 44 px high.** A mouse-only shrink is allowed with `@media (hover:hover) and (pointer:fine)`.
- **Text:** body 16 px; notes, tables and legends at least 14 px; chart labels at least 12 px.
- **Every table sits in a `.tw` scroll wrapper.**
- **Collapsible parts show a chevron** so people can see they open. Long pages put supporting content behind one tap on a phone and open it on wide screens.
- **Charts must work with a thumb:** no hover-only information, and marks big enough to tap or a readout line under the chart.
- Look at it with synthetic data only, never real conversations.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/). Conventions adopted on 30 Sep 2026; earlier commits predate them.

```
type(scope): imperative summary

Why the change was needed. The diff already shows what changed.

Co-authored-by: <AI agent, when one paired on the change>
```

- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.
- **Scopes:** `readers`, `classify`, `report`, `nudge`, `plugin`, `launcher`, `security`, `release`. Leave the scope out when none fits.
- **Summary:** imperative mood ("add", not "added"), 72 characters at most, no final period.
- **Body:** explain why, the trade-off, and how it was tested when that isn't obvious. Real numbers help ("on 455 local prompts only three labels changed").
- **One logical change per commit.** If the summary needs "and", split the commit.
- **AI pair-programming is credited** with a `Co-authored-by` trailer. I review and own every change.

## Workflow

1. Branch from `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>` or `chore/<topic>`.
2. Run the tests: `python3 -m unittest discover -s tests -v`.
3. Open a pull request and fill in the template. CI runs the tests on macOS, Linux and Windows (`.github/workflows/test.yml`).
4. Squash-merge into `main` and delete the branch. The squash message lists the branch's commits.
5. For a release, update `CHANGELOG.md` and the version, then tag `vX.Y.Z` ([Semantic Versioning](https://semver.org/)).

## Secrets

- Mirror needs no keys or tokens. If a change seems to need one, stop and rethink the change.
- [gitleaks](https://github.com/gitleaks/gitleaks) scans staged changes before every commit. Set it up once, from inside this folder:

```bash
brew install gitleaks pre-commit
pre-commit install
```
