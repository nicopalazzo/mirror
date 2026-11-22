# AI habits retro: facilitator script

One page for a 45-minute session with 5 or more people who use AI coding tools. You run Mirror on your own computer; nothing goes online.

## 🧭 Say this first

- "This is a retro about habits, not a review of people. The cards are **not for evaluation**: not for performance reviews, not for pay, not for staffing."
- "A card is optional. Nobody has to bring one, and nobody will ask why."
- "Managers in the room see the same ranges as everyone else, and nothing more."

If someone with a say over people's jobs asks for single cards, the session stops being a retro. Say no, or don't run it.

## 📨 Before the session (each person, on their own computer)

1. `python3 mirror.py share-card --json > my-card.json`
2. Open the file and read it. It holds five rounded numbers, a period, a week and the Mirror version: no name, no projects, no messages.
3. Send it to the facilitator only if you want to. Rename it to anything; the name is never shown.

## 🧮 Before the session (facilitator)

1. Put the cards in one folder. Don't open them one by one.
2. `python3 mirror.py team <folder> --open`
3. Mirror refuses with fewer than 5 cards. That is on purpose: with fewer, a range points at a person.
4. It writes a page, a text version and a summary (`.json`) in `~/Mirror`.

## 🗣️ During the session (30 minutes)

- Show the page. For each number, ask the group: "What spread surprises us, and what kind of work sits behind it?"
- Read the "What this cannot tell you" lines out loud once.
- Don't ask "whose is the high one". If someone volunteers their own number, that's their choice.
- Anyone who wants to place their own card does it on their own computer: `python3 mirror.py team <summary.json> --mine my-card.json`. It prints in their terminal only and writes nothing.

## 🧹 After the session

- Share the summary (`.json`) or the page, **not the folder of cards**.
- Delete the folder of cards.
- Each person decides alone what, if anything, they change. Mirror and the facilitator don't set targets.
