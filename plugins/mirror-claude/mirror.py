#!/usr/bin/env python3
"""Mirror: a local, read-only look at how you work with AI (Claude Code, Codex and Cursor).

Nothing leaves your computer. No network code, no installs, standard library only.
Run:  python3 mirror.py day      (Windows:  py mirror.py day)
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write(
        "Mirror needs Python 3.8 or newer; this is Python %d.%d.\n"
        "Get a current Python from https://www.python.org/downloads/ (on Windows also try: py -3 mirror.py day)\n"
        % sys.version_info[:2]
    )
    sys.exit(1)

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mirror_core import __version__, store
from mirror_core.explain import INDEXES, DISCLAIMER
from mirror_core.indexes import by_day, QUICK_SECONDS
from mirror_core.readers import default_dirs, read_claude, read_codex, read_cursor, inventory
from mirror_core.render_text import day_text, week_text, explain_text


CONSENT_VERSION = 2  # bumped when Mirror started reading Cursor chats, so everyone is asked again


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _dirs(args):
    claude_root, codex_root, cursor_root = default_dirs()
    if getattr(args, "claude_dir", None):
        claude_root = Path(args.claude_dir)
    if getattr(args, "codex_dir", None):
        codex_root = Path(args.codex_dir)
    if getattr(args, "cursor_dir", None):
        cursor_root = Path(args.cursor_dir)
    return claude_root, codex_root, cursor_root


def _load(args):
    claude_root, codex_root, cursor_root = _dirs(args)
    t1, a1, k1 = read_claude(claude_root, args.since)
    t2, a2, k2 = read_codex(codex_root, args.since)
    t3, a3, k3 = read_cursor(cursor_root, args.since)
    turns, actions = t1 + t2 + t3, a1 + a2 + a3
    tokens = {}
    for src in (k1, k2, k3):
        for m, v in src.items():
            tokens[m] = v
    missing = []
    if not t1 and not a1:
        missing.append(f"no Claude Code logs found in {claude_root / 'projects'}")
    if not t2 and not a2:
        missing.append(f"no Codex logs found in {codex_root / 'sessions'}")
    if not t3 and not a3:
        missing.append(f"no Cursor logs found in {cursor_root / 'projects'}")
    return turns, actions, tokens, missing, (claude_root, codex_root, cursor_root)


def _consent(args, roots):
    cfg = store.load_config()
    if cfg.get("consent_version") == CONSENT_VERSION:
        return True
    claude_root, codex_root, cursor_root = roots
    print("Mirror reads your own AI session logs, on this computer only.")
    print("  It will read:  " + str(claude_root / "projects") + "  (Claude Code sessions)")
    print("                 " + str(codex_root / "sessions") + "  (Codex sessions)")
    print("                 " + str(cursor_root / "projects" / "*" / "agent-transcripts") + "  (Cursor chats)")
    print("  It never opens anything else in those folders (no credentials, no settings).")
    print("  It never sends anything anywhere. It writes only to: " + str(store.home()) + "  (settings, your notes)")
    print("                                                        " + str(store.reports_dir()) + "  (report pages)")
    print("  Remove everything any time with:  mirror.py forget")
    if args.yes:
        ok = True
    elif sys.stdin.isatty():
        ok = input("Continue? [y/N] ").strip().lower() in ("y", "yes", "o", "oui")
    else:
        print("Not a terminal, so I can't ask. Re-run with --yes to agree.", file=sys.stderr)
        return False
    if ok:
        cfg["consent_version"] = CONSENT_VERSION
        cfg["consented_at"] = datetime.now().isoformat(timespec="seconds")
        store.save_config(cfg)
    return ok


def _pick_day(args, all_days):
    if args.day:
        return date.fromisoformat(args.day)
    if args.yesterday:
        return date.today() - timedelta(days=1)
    return date.today()


def cmd_sources(args):
    claude_root, codex_root, cursor_root = _dirs(args)
    print("Mirror looks here (it counts files without opening them):")
    for name, v in inventory(claude_root, codex_root, cursor_root).items():
        when = datetime.fromtimestamp(v["newest"]).strftime("%Y-%m-%d") if v["newest"] else "-"
        print(f"  {name:<12} {v['files']:>4} session files, {v['bytes'] / 1e6:6.1f} MB, newest {when}\n               {v['path']}")
    print("\nNote: Claude Code deletes old sessions after about 30 days unless you change `cleanupPeriodDays` in its settings.")


def cmd_day(args):
    turns, actions, tokens, missing, roots = _load(args)
    all_days = by_day(turns, actions, args.quick_seconds)
    d = _pick_day(args, all_days)
    if d not in all_days:
        print(f"No AI activity found for {d.isoformat()}.")
        if all_days:
            print("Most recent active day: " + max(all_days).isoformat() + "  (use --day YYYY-MM-DD)")
        for m in missing:
            print("Note: " + m)
        return 0
    print(day_text(d, all_days[d], all_days, missing))
    if sys.stdin.isatty() and not args.no_feedback:
        print("")
        ans = input("Does this match how your day felt? [y]es / [n]o / [p]artly / [s]kip: ").strip().lower()[:1]
        if ans in ("y", "n", "p"):
            note = input("Anything the numbers missed? (optional, stays on this computer): ").strip()
            s = all_days[d]
            store.add_feedback({
                "day": d.isoformat(), "match": {"y": "yes", "n": "no", "p": "partly"}[ans], "note": note,
                "numbers": {"prompts": s["prompts"], **s["idx"], "active_minutes": s["active_minutes"]},
            })
            print("Saved on this computer. Thank you.")
    return 0


def cmd_week(args):
    turns, actions, tokens, missing, roots = _load(args)
    all_days = by_day(turns, actions, args.quick_seconds)
    end = _pick_day(args, all_days)
    print(week_text(all_days, end))
    return 0


def cmd_report(args):
    from mirror_core.render_html import build
    turns, actions, tokens, missing, roots = _load(args)
    all_days = by_day(turns, actions, args.quick_seconds)
    out = store.reports_dir() / f"mirror-{date.today().isoformat()}.html"
    cov = {}
    for t in turns:
        c = cov.setdefault(t.tool, {"tool": t.tool, "dates": set(), "messages": 0})
        c["dates"].add(t.ts.date())
        c["messages"] += 1
    for a in actions:
        cov.setdefault(a.tool, {"tool": a.tool, "dates": set(), "messages": 0})["dates"].add(a.ts.date())
    coverage = [{"tool": v["tool"], "first": min(v["dates"]).isoformat(), "last": max(v["dates"]).isoformat(),
                 "days": len(v["dates"]), "messages": v["messages"]} for v in cov.values() if v["dates"]]
    build(all_days, store.read_feedback(), tokens, out, coverage)
    print("Report saved in your Mirror folder: " + str(out))
    print("Open it again any time with the 'Mirror Report' launcher, or: python3 mirror.py report --open")
    if args.open:
        import webbrowser
        webbrowser.open(out.as_uri())
    else:
        print("Open that file in your browser (it works offline), or re-run with --open.")
    return 0


def cmd_explain(args):
    if args.index not in INDEXES:
        print("Choose one of: " + ", ".join(INDEXES))
        return 2
    print(explain_text(args.index))
    return 0


def cmd_share(args):
    fb = store.read_feedback()
    if not fb:
        print("Nothing to share yet: run `day` and answer the last question first.")
        return 0
    card = []
    for x in fb[-args.last:]:
        item = {"day": x["day"], "match": x["match"], "numbers": x["numbers"]}
        if args.include_note:
            item["note"] = x.get("note", "")
        card.append(item)
    print("Numbers only. Your prompts are never included" + (" (notes included because you asked)." if args.include_note else ", and neither are your notes."))
    print(json.dumps(card, indent=2))
    print("\nYou choose whether to send this to anyone. Mirror sends nothing.")
    return 0


def cmd_doctor(args):
    """Prints versions and counts only, never message text. Paste this if something looks wrong."""
    import platform
    from collections import Counter
    claude_root, codex_root, cursor_root = _dirs(args)
    print(f"mirror {__version__}")
    print(f"python {platform.python_version()} on {platform.system()} {platform.release()} ({platform.machine()})")
    print("terminal encoding: " + str(getattr(sys.stdout, "encoding", "?")))
    for name, v in inventory(claude_root, codex_root, cursor_root).items():
        print(f"{name}: {v['files']} session files")
    if not _consent(args, (claude_root, codex_root, cursor_root)):
        return 1
    turns, actions, tokens, missing, roots = _load(args)
    print(f"parsed: {len(turns)} of your messages, {len(actions)} AI actions, {len(tokens)} models with token counts")
    print("message kinds: " + json.dumps(dict(Counter(t.kind for t in turns))))
    print("AI action kinds: " + json.dumps(dict(Counter(a.cat for a in actions))))
    for m in missing:
        print("note: " + m)
    print("If a tool has session files but 0 parsed messages, its log format may have changed. Send this output to the author.")
    return 0


def cmd_feedback(args):
    """Non-interactive version of the question at the end of `day`, for use from an assistant."""
    turns, actions, tokens, missing, roots = _load(args)
    all_days = by_day(turns, actions, args.quick_seconds)
    d = _pick_day(args, all_days)
    if d not in all_days:
        print(f"No AI activity found for {d.isoformat()}, so there is nothing to attach the answer to.")
        return 1
    s = all_days[d]
    store.add_feedback({
        "day": d.isoformat(), "match": args.match, "note": args.note or "",
        "numbers": {"prompts": s["prompts"], **s["idx"], "active_minutes": s["active_minutes"]},
    })
    print("Saved on this computer.")
    return 0


def cmd_nudge_hook(args):
    from mirror_core.nudge import hook_main
    out = hook_main(sys.stdin.read())
    if out:
        print(out)
    return 0


def cmd_nudge(args):
    from mirror_core import nudge
    if args.action == "on" and args.threshold:
        st = nudge.load()
        st["threshold"] = max(3, args.threshold)
        nudge.save(st)
    if args.action in nudge.SETTINGS:
        print(nudge.localize(nudge.configure(args.action, args.value)))
    elif args.action == "status":
        print(nudge.localize(nudge.status()))
    else:
        print(nudge.localize(nudge.respond(args.action, args.minutes)))
    return 0


def cmd_forget(args):
    print("Deleted " + str(store.home()) if store.forget() else "Nothing to delete.")
    return 0


def main(argv=None):
    _utf8()
    p = argparse.ArgumentParser(prog="mirror", description="A local, read-only look at how you work with AI. " + DISCLAIMER)
    p.add_argument("--version", action="version", version="mirror " + __version__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--since", type=int, default=60, help="only read sessions modified in the last N days (default 60)")
    common.add_argument("--yes", action="store_true", help="agree to the first-run notice without asking")
    common.add_argument("--claude-dir", help="Claude Code folder (default ~/.claude)")
    common.add_argument("--codex-dir", help="Codex folder (default ~/.codex)")
    common.add_argument("--cursor-dir", help="Cursor folder (default ~/.cursor)")
    common.add_argument("--quick-seconds", type=int, default=QUICK_SECONDS, help="what counts as a quick approval (default 15)")
    common.add_argument("--day", help="YYYY-MM-DD (default today)")
    common.add_argument("--yesterday", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("day", parents=[common], help="how today went").add_argument("--no-feedback", action="store_true")
    sub.add_parser("week", parents=[common], help="the last 7 days against your own earlier days")
    r = sub.add_parser("report", parents=[common], help="write the HTML report")
    r.add_argument("--open", action="store_true")
    sub.add_parser("sources", parents=[common], help="what Mirror can see (counts files, opens none)")
    e = sub.add_parser("explain", help="what a number means")
    e.add_argument("index", nargs="?", default="challenge")
    s = sub.add_parser("share-card", help="print numbers only, to send if you choose")
    s.add_argument("--last", type=int, default=7)
    s.add_argument("--include-note", action="store_true")
    fb = sub.add_parser("feedback", parents=[common], help="record whether a day's numbers matched how it felt")
    fb.add_argument("--match", required=True, choices=["yes", "no", "partly"])
    fb.add_argument("--note", default="")
    sub.add_parser("doctor", parents=[common], help="print versions and counts (no message text) to debug a setup")
    sub.add_parser("nudge-hook", help="(used by the plugin hook) read one prompt event from stdin")
    ng = sub.add_parser("nudge", help="turn nudges on/off, snooze them, or see their status")
    ng.add_argument("action", choices=["on", "off", "snooze", "check", "status",
                                       "holdback", "rule", "ratio-threshold", "window", "threshold", "cooldown"])
    ng.add_argument("value", nargs="?", help="with a setting: its new value, e.g. 'nudge rule ratio' or 'nudge holdback 0.5'")
    ng.add_argument("--minutes", type=int, default=None)
    ng.add_argument("--threshold", type=int, default=None, help="with 'on': messages without a question before a nudge")
    sub.add_parser("forget", help="delete everything Mirror stored")
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    if args.cmd in ("explain", "forget", "share-card", "nudge-hook", "nudge"):
        return {"explain": cmd_explain, "forget": cmd_forget, "share-card": cmd_share,
                "nudge-hook": cmd_nudge_hook, "nudge": cmd_nudge}[args.cmd](args)
    if args.cmd == "sources":
        return cmd_sources(args) or 0
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if not _consent(args, _dirs(args)):
        return 1
    return {"day": cmd_day, "week": cmd_week, "report": cmd_report, "doctor": cmd_doctor, "feedback": cmd_feedback}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
