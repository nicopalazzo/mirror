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
}

DISCLAIMER = (
    "Mirror is an exploration, not a test, a score or a diagnosis. It counts patterns in your own logs and "
    "labels your messages with simple rules that are sometimes wrong. Use the numbers as questions."
)
