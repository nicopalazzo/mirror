import ast
import builtins
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import make_fixtures  # noqa: E402
import mirror  # noqa: E402
from mirror_core.classify import classify  # noqa: E402
from mirror_core.readers import read_claude, read_codex, read_cursor  # noqa: E402
from mirror_core.indexes import by_day  # noqa: E402

FORBIDDEN_IMPORTS = {"socket", "ssl", "urllib", "http", "requests", "ftplib", "smtplib", "telnetlib", "xmlrpc",
                     "subprocess", "ctypes", "asyncio", "aiohttp", "httpx", "websocket", "websockets"}
FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile"}


def run_cli(argv, env):
    out = io.StringIO()
    with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
        code = mirror.main(argv)
    return code, out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.claude, self.codex, self.base = make_fixtures.build(self.root)
        self.cursor = self.root / "cursor"
        self.env = {"MIRROR_HOME": str(self.root / "home"), "MIRROR_CLAUDE_DIR": str(self.claude), "MIRROR_CODEX_DIR": str(self.codex),
                    "MIRROR_CURSOR_DIR": str(self.cursor)}

    def tearDown(self):
        self.tmp.cleanup()


class Classifier(unittest.TestCase):
    def test_english_and_french(self):
        cases = {
            "ok": "approval", "yes go ahead": "approval", "Parfait, merci": "approval", "vas-y": "approval",
            "Can you add a login page?": "directive", "Peux-tu créer un fichier ?": "directive",
            "why didn't you read it?": "challenge", "Pourquoi tu as oublié le bouton ?": "challenge",
            "I don't agree with that": "challenge", "Tu te trompes": "challenge",
            "What is the difference between a cookie and a token?": "question", "Comment ça marche ?": "question",
            "/model": "meta", "<command-name>/model</command-name>": "meta",
            "I think we should keep the design simple.": "context",
            # real misses from the 29 Sep live demo
            "Ok, maybe change this": "challenge", "Then it's not ok, I want you to explain why": "challenge",
            "ok but that's wrong": "challenge", "c'est pas ok, explique pourquoi": "challenge",
            "ok go": "approval", "ok no problem": "approval",
            "Maybe we can change the following items": "challenge",
        }
        for text, want in cases.items():
            self.assertEqual(classify(text), want, text)

    def test_long_paste(self):
        self.assertEqual(classify("x" * 2000), "pasted")


class Readers(Base):
    def test_claude(self):
        turns, actions, tokens = read_claude(self.claude)
        self.assertEqual(len(turns), 6)  # tool_result row skipped; the /model command is dropped at read time
        self.assertEqual(sum(1 for a in actions if a.cat == "write"), 3)
        self.assertEqual(tokens["claude-test-1"]["messages"], 5)

    def test_codex(self):
        turns, actions, tokens = read_codex(self.codex)
        self.assertEqual(len(turns), 2)
        self.assertEqual(sum(1 for a in actions if a.cat == "write"), 1)
        self.assertEqual(tokens["codex-test"]["cached"], 400)


class CursorReader(Base):
    def test_messages_actions_and_untimed(self):
        turns, actions, _ = read_cursor(self.cursor)
        self.assertEqual(sorted(t.kind for t in turns), ["approval", "challenge", "directive"])  # timestamp-only row and subagent ignored
        self.assertTrue(all(not a.timed for a in actions))
        self.assertEqual(sum(1 for a in actions if a.cat == "write"), 1)
        self.assertEqual(sum(1 for a in actions if a.cat == "research"), 1)
        self.assertEqual(len({t.session for t in turns}), 1)

    def test_no_text_kept(self):
        turns, actions, _ = read_cursor(self.cursor)
        self.assertNotIn("settings page", repr(turns) + repr(actions))
        self.assertNotIn("SUBAGENT", repr(turns) + repr(actions))

    def test_untimed_approval_is_not_counted_as_quick(self):
        t, a, _ = read_cursor(self.cursor)
        s = by_day(t, a)[self.base.date()]
        self.assertEqual(s["idx"]["quick_approvals"], 0)
        self.assertEqual(s["idx"]["approvals_after_writes"], 0)
        self.assertEqual(s["idx"]["approvals_untimed"], 1)


class Indexes(Base):
    def test_quick_approval_and_kinds(self):
        t1, a1, _ = read_claude(self.claude)
        t2, a2, _ = read_codex(self.codex)
        days = by_day(t1 + t2, a1 + a2)
        s = days[self.base.date()]
        self.assertEqual(s["idx"]["approvals_after_writes"], 3)  # ok, Parfait merci, yes go ahead
        self.assertEqual(s["idx"]["quick_approvals"], 2)          # ok (5 s) and codex yes (1 s)
        self.assertEqual(s["kinds"]["challenge"], 1)
        self.assertEqual(sorted(s["tools"]), ["Claude", "Codex"])  # Cursor is read separately in CursorReader


class Security(Base):
    def test_no_network_or_exec_code(self):
        offenders = []
        for py in list((ROOT / "mirror_core").glob("*.py")) + list((ROOT / "scripts").glob("*.py")) + [ROOT / "mirror.py"]:
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in FORBIDDEN_IMPORTS:
                        offenders.append((py.name, m))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    offenders.append((py.name, node.func.id))
                if isinstance(node, ast.Attribute) and node.attr in ("system", "popen") and getattr(node.value, "id", "") == "os":
                    offenders.append((py.name, "os." + node.attr))
        self.assertEqual(offenders, [])

    def test_only_session_files_are_opened(self):
        opened = []
        real_open = builtins.open

        def spy(file, mode="r", *a, **k):
            if "r" in mode and "+" not in mode:
                opened.append(str(file))
            return real_open(file, mode, *a, **k)

        with mock.patch("builtins.open", spy):
            code, _ = run_cli(["day", "--yes", "--no-feedback"], self.env)
            run_cli(["report", "--yes"], self.env)
            run_cli(["sources"], self.env)
        self.assertEqual(code, 0)
        outside = [p for p in opened if str(self.root / "home") not in p and not p.endswith(".jsonl")]
        self.assertEqual(outside, [], outside)
        bad = [p for p in opened if any(x in p for x in ("auth.json", "config.toml", "settings.json", "notes.txt", "mcp.json", "canvas", "subagents"))]
        self.assertEqual(bad, [])
        self.assertTrue(any(p.endswith("sess-1.jsonl") for p in opened))
        self.assertTrue(any(p.endswith("chat-1.jsonl") for p in opened))

    def test_report_is_offline_and_has_no_prompt_text(self):
        run_cli(["report", "--yes"], self.env)
        html = next((self.root / "home" / "reports").glob("*.html")).read_text(encoding="utf-8")
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))
        self.assertNotIn("https://", html)
        for phrase in ("login page", "cookie and a token", "renames files", "bouton de déconnexion"):
            self.assertNotIn(phrase, html)

    def test_share_card_has_numbers_only(self):
        store_dir = self.root / "home"
        store_dir.mkdir(exist_ok=True)
        (store_dir / "feedback.jsonl").write_text(json.dumps({"day": "2026-01-01", "match": "partly", "note": "SECRET NOTE", "numbers": {"prompts": 3}}) + "\n", encoding="utf-8")
        _, out = run_cli(["share-card"], self.env)
        self.assertNotIn("SECRET NOTE", out)
        _, out2 = run_cli(["share-card", "--include-note"], self.env)
        self.assertIn("SECRET NOTE", out2)


class Cli(Base):
    def test_day_output_and_no_text(self):
        code, out = run_cli(["day", "--yes", "--no-feedback"], self.env)
        self.assertEqual(code, 0)
        self.assertIn("Challenge rate", out)
        self.assertNotIn("login page", out)

    def test_consent_required_without_tty(self):
        code, _ = run_cli(["day"], self.env)
        self.assertEqual(code, 1)

    def test_forget(self):
        run_cli(["day", "--yes", "--no-feedback"], self.env)
        self.assertTrue((self.root / "home" / "config.json").exists())
        run_cli(["forget"], self.env)
        self.assertFalse((self.root / "home").exists())


class CodexPlugin(unittest.TestCase):
    P = ROOT / "plugins" / "mirror-codex"

    def test_engine_copy_matches_source(self):
        for f in list((ROOT / "mirror_core").glob("*.py")) + list((ROOT / "mirror_core").glob("*.html")) + [ROOT / "mirror.py"]:
            rel = f.relative_to(ROOT)
            self.assertEqual(f.read_bytes(), (self.P / rel).read_bytes(), f"{rel} is stale: run scripts/build_plugins.py")

    def test_copy_says_dollar_in_codex_copy(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, USERPROFILE=home)
            out = subprocess.run([sys.executable, str(self.P / "mirror.py"), "nudge", "on"], env=env,
                                 capture_output=True, text=True).stdout
        self.assertIn("$mirror:off", out)
        self.assertNotIn("/mirror:", out)

    def test_manifest_hook_skills_and_marketplace(self):
        man = json.loads((self.P / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(man["name"], "mirror")
        hooks = json.loads((self.P / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(list(hooks), ["UserPromptSubmit"])
        h = hooks["UserPromptSubmit"][0]["hooks"][0]
        self.assertIn("nudge-hook", h["command"])
        self.assertIn("PLUGIN_ROOT", h["command"])
        for skill in ("check", "on", "off", "snooze", "status"):
            text = (self.P / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"name: {skill}", text)
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)
            policy = (self.P / "skills" / skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn("allow_implicit_invocation: false", policy, skill)
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        entry = market["plugins"][0]
        self.assertEqual(entry["name"], man["name"])
        self.assertTrue((ROOT / entry["source"]["path"] / ".codex-plugin" / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()


class Doctor(Base):
    def test_doctor_prints_counts_not_text(self):
        code, out = run_cli(["doctor", "--yes"], self.env)
        self.assertEqual(code, 0)
        self.assertIn("parsed:", out)
        for phrase in ("login page", "cookie and a token", "renames files"):
            self.assertNotIn(phrase, out)


class NoTextKept(Base):
    def test_readers_return_no_message_text_or_paths(self):
        t1, a1, k1 = read_claude(self.claude)
        t2, a2, k2 = read_codex(self.codex)
        blob = repr(t1) + repr(a1) + repr(t2) + repr(a2) + repr(k1) + repr(k2)
        for phrase in ("login page", "cookie and a token", "renames files", "bouton de", "yes go ahead", "/home/demo", "-home-demo-app"):
            self.assertNotIn(phrase, blob)
        self.assertFalse(any(hasattr(t, "text") for t in t1 + t2))
        self.assertTrue(all(len(t.project) == 8 for t in t1 + t2))

    def test_commands_are_not_turns(self):
        t1, _, _ = read_claude(self.claude)
        self.assertNotIn("meta", {t.kind for t in t1})


class Feedback(Base):
    def test_feedback_command_and_share_card(self):
        code, _ = run_cli(["feedback", "--yes", "--match", "partly", "--note", "PRIVATE NOTE"], self.env)
        self.assertEqual(code, 0)
        _, card = run_cli(["share-card"], self.env)
        self.assertIn('"match": "partly"', card)
        self.assertNotIn("PRIVATE NOTE", card)


class Docs(unittest.TestCase):
    def test_skill_frontmatter(self):
        s = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(s.startswith("---\nname: mirror\ndescription: "))
        self.assertIn("Never open, read, list, search or copy anything in `~/.claude`", s)

    def test_threat_model_names_real_tests(self):
        import re
        doc = (ROOT / "THREAT-MODEL.md").read_text(encoding="utf-8")
        src = (ROOT / "tests" / "test_mirror.py").read_text(encoding="utf-8")
        names = set(re.findall(r"`(test_[a-z_]+)`", doc))
        self.assertTrue(names)
        for n in names:
            self.assertIn("def " + n, src, n)


class Launchers(unittest.TestCase):
    NETWORK_WORDS = ("curl", "wget", "invoke-webrequest", "bitsadmin", "certutil", "powershell", "ssh ", "scp ", "ftp", "nc ", "http://")

    def test_launchers_exist_and_do_not_fetch_anything(self):
        for name in ("Mirror.command", "Mirror.bat", "Mirror Report.command", "Mirror Report.bat"):
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            for w in self.NETWORK_WORDS:
                self.assertNotIn(w, text, name + " contains " + w)
            self.assertIn("mirror.py", text)

    def test_command_file_is_executable_and_bat_is_crlf(self):
        for n in ("Mirror.command", "Mirror Report.command"):
            if os.name != "nt":
                self.assertTrue(os.access(ROOT / n, os.X_OK), n)
            self.assertTrue((ROOT / n).read_text(encoding="utf-8").startswith("#!/bin/bash"))
        for n in ("Mirror.bat", "Mirror Report.bat"):
            self.assertIn(b"\r\n", (ROOT / n).read_bytes(), n)


class ReportsFolder(Base):
    def test_default_is_visible_home_folder_unless_home_overridden(self):
        from mirror_core import store
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MIRROR_HOME", None)
            os.environ.pop("MIRROR_REPORTS", None)
            self.assertEqual(store.reports_dir(), Path.home() / "Mirror")
        with mock.patch.dict(os.environ, {"MIRROR_HOME": str(self.root / "h")}):
            os.environ.pop("MIRROR_REPORTS", None)
            self.assertEqual(store.reports_dir(), self.root / "h" / "reports")
        self.assertNotIn(Path.home() / "Documents", [store.reports_dir()])

    def test_forget_removes_only_mirror_reports(self):
        rep = self.root / "visible"
        rep.mkdir()
        (rep / "mirror-2026-01-01.html").write_text("x", encoding="utf-8")
        (rep / "my-own-notes.txt").write_text("keep me", encoding="utf-8")
        env = dict(self.env, MIRROR_REPORTS=str(rep))
        run_cli(["day", "--yes", "--no-feedback"], env)
        run_cli(["forget"], env)
        self.assertFalse((rep / "mirror-2026-01-01.html").exists())
        self.assertTrue((rep / "my-own-notes.txt").exists())
        self.assertFalse((self.root / "home").exists())


class Nudge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MIRROR_HOME": self.tmp.name})
        self.env.start()
        from mirror_core import nudge
        self.n = nudge
        from datetime import datetime, timezone
        self.t0 = datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_prompts(self, texts, start, step_min=1, sid="s"):
        out = []
        for i, t in enumerate(texts):
            out.append(self.n.on_prompt(sid, t, now=start + timedelta(minutes=i * step_min)))
        return out

    def test_off_by_default_intro_once(self):
        out = self.run_prompts(["ok"] * 40, self.t0)
        self.assertEqual(out[0], self.n.INTRO)
        self.assertEqual([m for m in out[1:] if m], [])

    def test_fires_at_threshold_and_resets(self):
        self.n.respond("on", now=self.t0)
        out = self.run_prompts(["go ahead"] * 30, self.t0)
        self.assertIn("30 messages", out[29])
        self.assertEqual([m for m in out[:29] if m], [])

    def test_question_or_pushback_resets_streak(self):
        self.n.respond("on", now=self.t0)
        out = self.run_prompts(["ok"] * 20 + ["why did you skip the tests?"] + ["ok"] * 20, self.t0)
        self.assertEqual([m for m in out if m], [])

    def test_commands_and_pastes_not_counted(self):
        self.n.respond("on", now=self.t0)
        out = self.run_prompts(["/model", "/mirror:status", "x" * 3000] * 20, self.t0)
        self.assertEqual([m for m in out if m], [])

    def test_cooldown_and_snooze(self):
        self.n.respond("on", now=self.t0)
        out = self.run_prompts(["ok"] * 60, self.t0)  # 60 minutes: second streak inside the 2 h cooldown
        self.assertEqual(len([m for m in out if m]), 1)
        self.n.respond("snooze", minutes=600, now=self.t0 + timedelta(hours=3))
        out = self.run_prompts(["ok"] * 40, self.t0 + timedelta(hours=3))
        self.assertEqual([m for m in out if m], [])

    def test_off_stops_everything(self):
        self.n.respond("on", now=self.t0)
        self.n.respond("off", now=self.t0)
        out = self.run_prompts(["ok"] * 40, self.t0)
        self.assertEqual([m for m in out if m], [])

    def test_ignored_nudges_back_off_then_step_back(self):
        self.n.respond("on", now=self.t0)
        msgs = []
        t = self.t0
        for _ in range(4):
            out = self.run_prompts(["ok"] * 30, t)
            msgs += [m for m in out if m]
            t += timedelta(hours=20)  # beyond any cooldown multiple
        self.assertEqual(msgs[-1], self.n.STEP_BACK)
        out = self.run_prompts(["ok"] * 30, t)
        self.assertEqual([m for m in out if m], [])  # quiet for a day

    def test_answering_resets_ignored_count(self):
        self.n.respond("on", now=self.t0)
        self.run_prompts(["ok"] * 30, self.t0)
        self.n.respond("check", now=self.t0 + timedelta(minutes=31))
        self.assertEqual(self.n.load()["ignored_in_row"], 0)
        self.assertIn("check 1", self.n.status())

    def test_pushback_after_nudge_counts_as_acted(self):
        self.n.respond("on", now=self.t0)
        self.run_prompts(["ok"] * 30, self.t0)  # nudge on the 30th
        st = self.n.load(); st["ignored_in_row"] = 2; self.n.save(st)
        self.n.on_prompt("s", "Then it's not ok, explain why", now=self.t0 + timedelta(minutes=31))
        st = self.n.load()
        self.assertFalse(st["pending"])
        self.assertEqual(st["ignored_in_row"], 0)
        self.assertIn("acted (asked or pushed back) 1", self.n.status())

    def test_sending_anyway_counts_as_ignored(self):
        self.n.respond("on", now=self.t0)
        self.run_prompts(["ok"] * 30, self.t0)
        self.n.on_prompt("s", "ok", now=self.t0 + timedelta(minutes=31))
        st = self.n.load()
        self.assertFalse(st["pending"])
        self.assertEqual(st["ignored_in_row"], 1)
        self.assertIn("sent anyway 1", self.n.status())

    def test_new_instruction_after_nudge_counts_as_edited(self):
        self.n.respond("on", now=self.t0)
        self.run_prompts(["ok"] * 30, self.t0)
        st = self.n.load(); st["ignored_in_row"] = 2; self.n.save(st)
        self.n.on_prompt("s", "Now write the tests for the payment step", now=self.t0 + timedelta(minutes=31))
        self.assertEqual(self.n.load()["ignored_in_row"], 0)
        self.assertIn("edited 1", self.n.status())

    def test_state_holds_no_prompt_text(self):
        self.n.respond("on", now=self.t0)
        self.run_prompts(["SECRET CLIENT NAME ok"] * 35 + ["why SECRET?"], self.t0)
        raw = (Path(self.tmp.name) / "nudge.json").read_text(encoding="utf-8")
        self.assertNotIn("SECRET", raw)

    def test_hook_never_raises(self):
        self.assertEqual(self.n.hook_main("not json"), "")
        self.assertEqual(self.n.hook_main('{"user_prompt": null}'), json.dumps({"systemMessage": self.n.INTRO}))

    def test_hook_reads_both_prompt_keys_and_blocks_on_nudge(self):
        self.n.respond("on", now=self.t0)
        st = self.n.load(); st["threshold"] = 3; self.n.save(st)
        outs = [self.n.hook_main(json.dumps({"session_id": "a", "prompt": "ok"})) for _ in range(3)]
        self.assertEqual(outs[:2], ["", ""])
        out = json.loads(outs[2])
        self.assertEqual(out["decision"], "block")
        self.assertIn("Mirror held this message", out["reason"])
        st = self.n.load(); st["last_nudge"] = None; self.n.save(st)
        outs = [self.n.hook_main(json.dumps({"session_id": "b", "user_prompt": "ok"})) for _ in range(3)]
        self.assertEqual(json.loads(outs[2])["decision"], "block")


class NudgeExperiment(Nudge):
    """Ratio rule and hold-back arm (5 Oct 2026)."""

    def on(self, **settings):
        self.n.respond("on", now=self.t0)
        for k, v in settings.items():
            self.assertNotIn("must be", self.n.configure(k, v))

    def test_holdback_withholds_and_logs(self):
        self.on(holdback="0.9", threshold="5")
        with mock.patch.object(self.n, "_rand", lambda: 0.0):
            out = self.run_prompts(["ok"] * 5, self.t0)
        self.assertEqual([m for m in out if m], [])
        st = self.n.load()
        self.assertEqual([e["event"] for e in st["log"]][-1], "withheld")
        self.assertEqual(st["pending_arm"], "held")
        self.assertIsNotNone(st["last_nudge"])  # held-back moments start the cooldown too

    def test_held_back_cooldown_matches_shown(self):
        self.on(holdback="0.9", threshold="5", cooldown="45")
        with mock.patch.object(self.n, "_rand", lambda: 0.0):
            out = self.run_prompts(["ok"] * 10, self.t0)  # second streak inside 45 min
        self.assertEqual(len([e for e in self.n.load()["log"] if e["event"] == "withheld"]), 1)

    def test_sent_anyway_after_held_back_is_not_ignored(self):
        self.on(holdback="0.9", threshold="5")
        with mock.patch.object(self.n, "_rand", lambda: 0.0):
            self.run_prompts(["ok"] * 5, self.t0)
            self.n.on_prompt("s", "ok", now=self.t0 + timedelta(minutes=6))
        st = self.n.load()
        self.assertEqual(st["ignored_in_row"], 0)
        resp = [e for e in st["log"] if e["event"] == "response"][-1]
        self.assertEqual((resp["response"], resp["arm"]), ("sent_anyway", "held"))

    def test_shown_arm_unchanged_and_status_compares_arms(self):
        self.on(holdback="0.5", threshold="5", cooldown="5")
        t = self.t0
        for i, (r, answer) in enumerate(((0.9, "why did you do that?"), (0.1, "ok"), (0.9, "ok"), (0.1, "why?"))):
            sid = f"round{i}"  # a fresh session per round so streaks do not carry over
            with mock.patch.object(self.n, "_rand", lambda r=r: r):
                out = self.run_prompts(["ok"] * 5, t, sid=sid)
            if r >= 0.5:
                self.assertIn("5 messages", out[-1])
            else:
                self.assertIsNone(out[-1])
            self.n.on_prompt(sid, answer, now=t + timedelta(minutes=6))
            t += timedelta(minutes=30)
        line = self.n.status().splitlines()[-1]
        self.assertIn("shown 2 moments, acted 50%", line)
        self.assertIn("held back 2 moments, acted 50%", line)
        self.assertIn("+0 points", line)

    def test_action_copy_is_off_by_default(self):
        self.assertEqual(self.n.load()["action_copy"], 0.0)
        self.on(threshold="5")
        out = self.run_prompts(["ok"] * 5, self.t0)
        self.assertIn("Review Claude's last answer?", out[-1])
        self.assertEqual([e for e in self.n.load()["log"] if e["event"] == "nudge"][-1]["variant"], "plain")
        self.assertNotIn("Copy test", self.n.status())

    def test_action_copy_asks_for_a_line_and_logs_variant(self):
        self.on(threshold="5", **{"action-copy": "0.5"})
        with mock.patch.object(self.n, "_rand", lambda: 0.1):
            out = self.run_prompts(["ok"] * 5, self.t0)
        self.assertIn("add one line", out[-1])
        self.assertNotIn("Review Claude's last answer?", out[-1])
        self.assertIn("Enter: send anyway", out[-1])  # still not enforced
        self.n.on_prompt("s", "it changes the nudge copy, so add a test", now=self.t0 + timedelta(minutes=6))
        resp = [e for e in self.n.load()["log"] if e["event"] == "response"][-1]
        self.assertEqual((resp["response"], resp["variant"]), ("edited", "action"))
        self.assertIn("add-a-line 1 nudges, acted 0%, acted or edited 100%", self.n.status())

    def test_action_copy_plain_arm_when_coin_is_high(self):
        self.on(threshold="5", **{"action-copy": "0.5"})
        with mock.patch.object(self.n, "_rand", lambda: 0.9):
            out = self.run_prompts(["ok"] * 5, self.t0)
        self.assertIn("Review Claude's last answer?", out[-1])
        self.assertEqual(self.n.load()["pending_variant"], "plain")

    def test_ratio_fires_where_streak_would_not(self):
        self.on(rule="ratio", **{"ratio-threshold": "0.9"})
        out = self.run_prompts(["ok"] * 14 + ["why is this failing?"] + ["ok"] * 5, self.t0)
        self.assertEqual([m for m in out[:19] if m], [])  # not before the window of 20 is full
        self.assertIn("19 of your last 20", out[19])
        ev = [e for e in self.n.load()["log"] if e["event"] == "nudge"][-1]
        self.assertEqual((ev["rule"], ev["r"]), ("ratio", 0.95))

    def test_ratio_below_threshold_and_window_cleared(self):
        self.on(rule="ratio", **{"ratio-threshold": "0.9"})
        out = self.run_prompts((["ok"] * 3 + ["why?"]) * 10, self.t0)  # 75% passive
        self.assertEqual([m for m in out if m], [])
        self.on(rule="ratio", **{"ratio-threshold": "0.75", "cooldown": "5"})
        out = self.run_prompts(["ok"] * 20, self.t0 + timedelta(hours=1), sid="t")
        self.assertTrue(out[19])
        sess = self.n.load()["sessions"]["t"]
        self.assertEqual(sess["recent"], [])  # cleared after firing

    def test_ratio_windows_are_per_session(self):
        self.on(rule="ratio")
        out = [self.n.on_prompt("a" if i % 2 else "b", "ok", now=self.t0 + timedelta(minutes=i)) for i in range(30)]
        self.assertEqual([m for m in out if m], [])  # each session has only 15

    def test_bad_settings_are_refused(self):
        self.assertIn("must be", self.n.configure("holdback", "2"))
        self.assertIn("must be", self.n.configure("action-copy", "1.5"))
        self.assertIn("must be", self.n.configure("rule", "sometimes"))
        self.assertIn("Unknown", self.n.configure("colour", "red"))
        self.assertEqual(self.n.load()["holdback"], 0.0)

    def test_experiment_state_holds_no_prompt_text(self):
        self.on(rule="ratio", holdback="0.5")
        self.run_prompts(["SECRET ok"] * 45 + ["why SECRET?"], self.t0)
        raw = (Path(self.tmp.name) / "nudge.json").read_text(encoding="utf-8")
        self.assertNotIn("SECRET", raw)

    def test_cli_sets_values(self):
        from contextlib import redirect_stdout
        import io
        sys.path.insert(0, str(ROOT))
        import mirror as cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["nudge", "holdback", "0.5"])
            cli.main(["nudge", "rule", "ratio"])
        self.assertIn("holdback set to 0.5", buf.getvalue())
        self.assertEqual(self.n.load()["rule"], "ratio")


class ClaudePlugin(unittest.TestCase):
    P = ROOT / "plugins" / "mirror-claude"

    def test_engine_copy_matches_source(self):
        for f in list((ROOT / "mirror_core").glob("*.py")) + list((ROOT / "mirror_core").glob("*.html")) + [ROOT / "mirror.py"]:
            rel = f.relative_to(ROOT)
            self.assertEqual(f.read_bytes(), (self.P / rel).read_bytes(), f"{rel} is stale: run scripts/build_plugins.py")

    def test_manifest_hook_and_skills(self):
        man = json.loads((self.P / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(man["name"], "mirror")
        hooks = json.loads((self.P / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(list(hooks), ["UserPromptSubmit"])
        h = hooks["UserPromptSubmit"][0]["hooks"][0]
        self.assertNotIn("async", h)  # async hooks send systemMessage to Claude, not the user
        self.assertIn("nudge-hook", h["command"])
        for skill in ("check", "on", "off", "snooze", "status", "report"):
            text = (self.P / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", text, skill)
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["plugins"][0]["name"], man["name"])

    def test_report_command_opens_report_and_never_agrees_for_the_user(self):
        text = (self.P / "skills" / "report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("mirror.py\" report --open", text)
        self.assertNotIn("--yes", text)  # the first-run agreement stays the user's decision
