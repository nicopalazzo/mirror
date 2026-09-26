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
from mirror_core.readers import read_claude, read_codex  # noqa: E402
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
        self.env = {"MIRROR_HOME": str(self.root / "home"), "MIRROR_CLAUDE_DIR": str(self.claude), "MIRROR_CODEX_DIR": str(self.codex)}

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
        }
        for text, want in cases.items():
            self.assertEqual(classify(text), want, text)

    def test_long_paste(self):
        self.assertEqual(classify("x" * 2000), "pasted")


class Readers(Base):
    def test_claude(self):
        turns, actions, tokens = read_claude(self.claude)
        self.assertEqual(len(turns), 7)  # tool_result row skipped
        self.assertEqual(sum(1 for a in actions if a.cat == "write"), 3)
        self.assertEqual(tokens["claude-test-1"]["messages"], 5)

    def test_codex(self):
        turns, actions, tokens = read_codex(self.codex)
        self.assertEqual(len(turns), 2)
        self.assertEqual(sum(1 for a in actions if a.cat == "write"), 1)
        self.assertEqual(tokens["codex-test"]["cached"], 400)


class Indexes(Base):
    def test_quick_approval_and_kinds(self):
        t1, a1, _ = read_claude(self.claude)
        t2, a2, _ = read_codex(self.codex)
        turns = t1 + t2
        for t in turns:
            t.kind = classify(t.text)
        turns = [t for t in turns if t.kind != "meta"]
        days = by_day(turns, a1 + a2)
        s = days[self.base.date()]
        self.assertEqual(s["idx"]["approvals_after_writes"], 3)  # ok, Parfait merci, yes go ahead
        self.assertEqual(s["idx"]["quick_approvals"], 2)          # ok (5 s) and codex yes (1 s)
        self.assertEqual(s["kinds"]["challenge"], 1)
        self.assertEqual(sorted(s["tools"]), ["Claude", "Codex"])


class Security(Base):
    def test_no_network_or_exec_code(self):
        offenders = []
        for py in list((ROOT / "mirror_core").glob("*.py")) + [ROOT / "mirror.py"]:
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
        bad = [p for p in opened if any(x in p for x in ("auth.json", "config.toml", "settings.json", "notes.txt"))]
        self.assertEqual(bad, [])
        self.assertTrue(any(p.endswith("sess-1.jsonl") for p in opened))

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


if __name__ == "__main__":
    unittest.main()


class Doctor(Base):
    def test_doctor_prints_counts_not_text(self):
        code, out = run_cli(["doctor", "--yes"], self.env)
        self.assertEqual(code, 0)
        self.assertIn("parsed:", out)
        for phrase in ("login page", "cookie and a token", "renames files"):
            self.assertNotIn(phrase, out)
