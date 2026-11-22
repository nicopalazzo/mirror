"""Plain-language meaning of each number. Wording matters: these are mirrors, not verdicts."""

INDEXES = {
    "challenge": {
        "title": "Challenge rate",
        "measures": "Of your real prompts, the share that push back on the AI (\"that's wrong\", \"why didn't you...\", \"are you sure\") and the share that ask a question.",
        "cannot": "It cannot tell whether the AI was right. Few pushbacks can mean you trusted a good answer, or that you did not look closely. It only shows how often you spoke up.",
        "ask": "What did the AI say today that I accepted without asking how it knew?",
        "practice": "Ask for the strongest objection to an answer before you use it, and say what would change your mind.",
    },
    "approval": {
        "title": "Approval share and quick approvals",
        "measures": "Share of your prompts that are short agreements (\"ok\", \"go\", \"vas-y\"). Quick approvals are agreements that arrived within 15 seconds of an AI turn that changed files.",
        "cannot": "A quick \"ok\" can be a well-informed decision or a skim. The 15-second line is arbitrary; you can change it with --quick-seconds. Cursor's logs have no reply times, so its approvals cannot be timed.",
        "ask": "Which change did I approve today that I could not explain in my own words?",
        "practice": "Before you accept a change, say one thing it does and one thing you would check.",
    },
    "delegation": {
        "title": "Delegation depth (actions per prompt, longest run of writes)",
        "measures": "How many things the AI did for each thing you typed, and the longest stretch of file changes with no message from you in between.",
        "cannot": "High numbers are normal for automated work. It does not say the work was wrong or that you should intervene.",
        "ask": "In the longest run today, at what point would I have wanted to look?",
        "practice": "For work that matters, ask the AI to pause after each file change or each step.",
    },
    "size": {
        "title": "Reply time against change size",
        "measures": "A run is the file changes the AI made with no message from you in between. For each run, Mirror counts the lines changed (added plus removed), how long the AI kept working after its first change, and how long you took to send your next message, of any kind. Runs are grouped as under 20 lines, 20 to 200, and over 200. Each group shows the median of both times and the share of runs you answered with a short agreement within 15 seconds. A group with fewer than 5 runs is not shown. Only the line count is kept, never the code.",
        "cannot": "A short gap is not proof you skipped the change: you may have read it while the AI was still working, which is why the run's own length sits next to your reply time. Lines say nothing about difficulty: 300 renamed lines can be easier to check than 5 lines of logic. Changes you read in your editor or in git are invisible here. Cursor's log has no reply times, so it is left out.",
        "ask": "Which big change did I answer as fast as a small one?",
    },
    "focus": {
        "title": "Focus (sessions, projects, tools, active time)",
        "measures": "How many separate sessions, projects and tools you touched, and how long you were actively exchanging with AI (gaps over 5 minutes are not counted).",
        "cannot": "Switching is not always a problem. It shows the shape of the day, not its quality.",
        "ask": "Which switch today pulled me away from what I meant to finish?",
        "practice": "Write down the one thing you are finishing before you open a second session.",
    },
    "team": {
        "title": "Team mirror (ranges from cards people chose to share)",
        "measures": "For five or more numbers-only cards that people made with `share-card --json` and handed over themselves: the median and the middle half (25th to 75th percentile) of each number. Never the lowest or highest card, a rank, or who sent which card.",
        "cannot": "The labels are rough: Mirror agrees with a person on about 86% of messages for question-or-pushback against the rest, and that error adds up across people. These numbers are not for judging anyone: a high or low number does not say whether someone works well, and different work gives different numbers. In a small group a range can still point at someone, so Mirror refuses under 5 cards, and even at 5 people may guess. It cannot tell whether one person sent two cards, or whether a card was edited.",
        "ask": "What spread surprises us, and what kind of work sits behind it?",
        "practice": "Talk about the spread as a group, then let each person decide on their own computer what, if anything, they change.",
    },
    "marks": {
        "title": "Before and after a change you named",
        "measures": "Your four numbers in the 4 weeks before a day you marked with `mirror.py mark`, next to the 4 weeks from that day on, with your usual weekly range beside them.",
        "cannot": "It cannot tell you that your change caused the difference. Many things change at once: the work, the project, the season, the AI tools themselves. Four weeks can also be too short to tell a real shift from an ordinary swing.",
        "ask": "What else changed around the day I marked?",
        "practice": "Mark the day you make a change, not weeks later, and keep the words short enough to recognise.",
    },
    "drift": {
        "title": "Session drift (how your messages change over a stretch and by hour)",
        "measures": "A stretch is your messages in one session with no gap over 30 minutes. For each part of a stretch (the first 30 minutes, 30 to 60, 60 to 120, after 120) and for each hour of the day: the share of your messages that ask a question or push back, the middle (median) length of your messages in characters, and the share of approvals after file changes that came within 15 seconds. Counts are added up first, then the share is worked out. A part with fewer than 5 messages (or 5 timed approvals) is hidden.",
        "cannot": "Fewer questions late in a stretch can mean the task got clear, not that you were tired. Shorter messages can mean you were in the flow, or that the AI needed less from you. Long stretches are rarer, so their parts rest on fewer messages. It shows how your messages changed, not why, and not whether the change was good.",
        "ask": "In my longest stretch, what changed in how I wrote to the AI, and did I mean that change?",
    },
}

# One line each, shown on the team page and in its text version.
TEAM_CANNOT = [
    "The labels are rough. Mirror agrees with a person on about 86% of messages for question-or-pushback against the rest, and comparing people adds up that error.",
    "These numbers are not for judging anyone. Different work gives different numbers, and a number does not say whether someone works well.",
    "In a small group a range can still point at someone. Mirror refuses under 5 cards, but even at 5 people may guess.",
    "It cannot tell whether one person sent two cards, or whether a card was edited by hand.",
]

DISCLAIMER = (
    "Mirror is an exploration, not a test, a score or a diagnosis. It counts patterns in your own logs and "
    "labels your messages with simple rules that are sometimes wrong. Use the numbers as questions."
)
