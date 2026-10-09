# Security and privacy

Mirror reads the session logs of AI tools on your own computer, so a privacy problem matters as much as a security one.

## Reporting a problem

- **Use GitHub's private reporting:** open the repository's **Security** tab and choose **Report a vulnerability**. That keeps the report private until it is fixed.
- If a private report is not possible, open an issue with the **Privacy concern** template and describe the behaviour in words only.
- **Never paste message text, report pages, file names or paths from your own logs** into an issue, a pull request or a comment. Numbers from `mirror.py doctor` are fine; it prints versions and counts, no text.

## What counts

- Anything that makes Mirror send data over a network, or imports a networking library. A test fails if one is added.
- Anything that reads files outside the session folders listed in the [README](README.md), or opens credentials, settings or MCP configuration.
- Any report, share card or setting file that contains message text or a guess typed into the quiz.
- A launcher or plugin that downloads or runs something other than `mirror.py`.

The [threat model](THREAT-MODEL.md) says who Mirror protects you from, how to check each protection, and what it does not cover.

## Supported versions

Only the latest release is supported. Mirror is an exploration (version 0.x), maintained by one person, so replies can take a few days.
