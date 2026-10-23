# Getting started with Mirror (5 minutes)

Mirror reads the logs your AI coding tool already keeps on your computer and shows you how you work with it. It runs only on your computer and sends nothing anywhere.

## Step 0: can you use it?

You need **one of these three tools**, used for at least a few days: **Claude Code, Codex or Cursor**.

- Web chats (claude.ai, chatgpt.com) leave no log on your computer, so Mirror cannot see them. If that is all you use, stop here.
- The one-time quiz needs about 30 messages. With fewer, you go straight to the report.

## Step 1: download

1. Download the zip: **[mirror-0.3.1.zip](https://github.com/nicopalazzo/mirror/archive/refs/tags/v0.3.1.zip)**
2. Unzip it. **Mac:** double-click the zip. **Windows:** right-click the zip, **Extract All**, and open the new folder. Do not run Mirror from inside the zip.

## Step 2: start it

**Mac:** open the folder and double-click **`Mirror.command`**.

- If your Mac says it "cannot be opened because it is from an unidentified developer": right-click the file, choose **Open**, then **Open** again.
- If double-clicking does nothing, open **Terminal**, type `cd ` (with a space), drag the unzipped folder onto the window, press Enter, then run `python3 mirror.py report --open`.
- If it says Python is missing, install it from [python.org/downloads](https://www.python.org/downloads/) and try again.

**Windows:** open the folder and double-click **`Mirror.bat`**.

- If Windows says "Windows protected your PC": click **More info**, then **Run anyway**.
- If it says Python is missing, install it from [python.org/downloads](https://www.python.org/downloads/). Tick **Add python.exe to PATH** in the installer, then try again.

## Step 3: what you will see

1. **A list of exactly what Mirror will read.** It only opens your AI tools' session files. Type `y` and press Enter if you agree. Type anything else to stop.
2. **A short note** saying your first report opens with a quiz.
3. **Your browser opens with 4 questions.** Guess a number for each (a rough guess is fine). Do not refresh the page: your guesses live only in the page.
4. **The reveal:** each guess next to what Mirror counted. A gap is not right or wrong. Mirror's rules are simple and sometimes wrong, so treat each one as a question to ask yourself.

To open the report again later, double-click **`Mirror Report.command`** (Mac) or **`Mirror Report.bat`** (Windows). Your reports are kept in a folder called **Mirror** in your home folder.

## If something goes wrong

- **The window closes at once.** Run it from a terminal instead (Mac: `python3 mirror.py report --open`; Windows: `py mirror.py report --open`) and read the message.
- **"No AI activity found".** Mirror found no logs. Check which tool you use. Claude Code deletes logs older than about 30 days by default.
- **Anything else.** Run `python3 mirror.py doctor` (Windows: `py mirror.py doctor`). It prints versions and counts, no text.

**When you report a problem, never paste message text, report pages or file paths from your own logs.** Numbers from `doctor` are fine. [Open an issue](https://github.com/nicopalazzo/mirror/issues/new/choose) or message the person who sent you this.

## Remove everything

`python3 mirror.py forget` (Windows: `py mirror.py forget`) deletes Mirror's settings and report files. Your AI tools' logs are never touched. Then delete the unzipped folder.

## Want to know exactly what it does?

[README](../README.md) for the full list, [THREAT-MODEL](../THREAT-MODEL.md) for who it protects you from. The code is short: start with `mirror_core/readers.py`.
