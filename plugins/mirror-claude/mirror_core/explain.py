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
    "focus": {
        "title": "Focus (sessions, projects, tools, active time)",
        "measures": "How many separate sessions, projects and tools you touched, and how long you were actively exchanging with AI (gaps over 5 minutes are not counted).",
        "cannot": "Switching is not always a problem. It shows the shape of the day, not its quality.",
        "ask": "Which switch today pulled me away from what I meant to finish?",
        "practice": "Write down the one thing you are finishing before you open a second session.",
    },
    "drift": {
        "title": "Session drift (how your messages change over a stretch and by hour)",
        "measures": "A stretch is your messages in one session with no gap over 30 minutes. For each part of a stretch (the first 30 minutes, 30 to 60, 60 to 120, after 120) and for each hour of the day: the share of your messages that ask a question or push back, the middle (median) length of your messages in characters, and the share of approvals after file changes that came within 15 seconds. Counts are added up first, then the share is worked out. A part with fewer than 5 messages (or 5 timed approvals) is hidden.",
        "cannot": "Fewer questions late in a stretch can mean the task got clear, not that you were tired. Shorter messages can mean you were in the flow, or that the AI needed less from you. Long stretches are rarer, so their parts rest on fewer messages. It shows how your messages changed, not why, and not whether the change was good.",
        "ask": "In my longest stretch, what changed in how I wrote to the AI, and did I mean that change?",
    },
}

DISCLAIMER = (
    "Mirror is an exploration, not a test, a score or a diagnosis. It counts patterns in your own logs and "
    "labels your messages with simple rules that are sometimes wrong. Use the numbers as questions."
)
