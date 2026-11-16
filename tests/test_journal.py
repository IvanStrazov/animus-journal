"""End-to-end tests for scripts/journal.py (stdlib unittest, no dependencies)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "journal.py"


def find_bash():
    """The shell Claude Code runs hooks in: bash, or Git Bash on Windows (not WSL's System32 bash.exe)."""
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    candidates = [Path(git).resolve().parent.parent / "bin" / "bash.exe"] if git else []
    candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe")
    return next((str(c) for c in candidates if c.is_file()), None)


BASH = find_bash()


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.global_dir = self.tmp / "global-journal"
        self.env = dict(os.environ, JOURNAL_GLOBAL_DIR=str(self.global_dir), PYTHONIOENCODING="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_j(self, *args, stdin="", cwd=None, env=None):
        r = subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, cwd=str(cwd or self.proj),
                           env=env or self.env, capture_output=True, text=True, encoding="utf-8")
        return r

    def add(self, title, tags, body):
        r = self.run_j("add", "--title", title, "--tags", tags, stdin=body)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_add_creates_layout_and_gitignore(self):
        self.add("First", "task-a,api", "Goal: g\nDone: d")
        j = self.proj / ".journal"
        self.assertEqual((j / ".gitignore").read_text(encoding="utf-8"), "*\n")
        self.assertIn("| #task-a #api | First", (j / "INDEX.md").read_text(encoding="utf-8"))
        logs = list((j / "log").glob("*.md"))
        self.assertEqual(len(logs), 1)
        self.assertIn("#task-a #api — First", logs[0].read_text(encoding="utf-8"))

    def test_entry_is_capped(self):
        r = self.add("Long", "t", "\n".join(f"line {i}" for i in range(50)))
        self.assertIn("trimmed to 20", r.stderr)
        text = next((self.proj / ".journal" / "log").glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("line 19", text)
        self.assertNotIn("line 20", text)

    def test_state_is_capped_and_overwritten(self):
        self.run_j("state", stdin="old")
        r = self.run_j("state", stdin="\n".join(f"s{i}" for i in range(60)))
        self.assertIn("trimmed to 40", r.stderr)
        lines = (self.proj / ".journal" / "STATE.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 40)
        self.assertNotIn("old", lines)

    def test_env_overrides_budget(self):
        env = dict(self.env, JOURNAL_STATE_MAX="5")
        self.run_j("state", stdin="\n".join(map(str, range(10))), env=env)
        self.assertEqual(len((self.proj / ".journal" / "STATE.md").read_text(encoding="utf-8").splitlines()), 5)

    def test_find_newest_first_and_limit(self):
        for i in range(5):
            self.add(f"Session {i}", "parser", f"Done: step {i}")
        self.add("Other", "ui", "Done: unrelated")
        out = self.run_j("find", "parser").stdout
        self.assertEqual(out.count("## "), 3)
        self.assertLess(out.index("Session 4"), out.index("Session 3"))
        self.assertNotIn("Other", out)
        self.assertEqual(self.run_j("find", "parser", "--all").stdout.count("## "), 5)
        self.assertIn("nothing found", self.run_j("find", "nope").stdout)

    def test_unicode_roundtrip(self):
        self.add("Naïve café parser", "café-ünïcode", "Décision: regex → ok")
        self.assertIn("Décision: regex → ok", self.run_j("find", "café").stdout)
        self.assertIn("#café-ünïcode(1)", self.run_j("tags").stdout)

    def test_context_budget(self):
        self.run_j("state", stdin="\n".join("x" * 60 for _ in range(40)))
        for i in range(8):
            self.add(f"Session {i}", "t", "Done: x")
        out = self.run_j("context", stdin=json.dumps({"cwd": str(self.proj)})).stdout
        self.assertIn("[journal] dir:", out)
        self.assertNotIn("Session 2", out)
        self.assertIn("Session 7", out)
        self.assertLess(len(out.encode("utf-8")), 4096 + len(str(self.tmp)) * 2)

    def test_context_without_journal(self):
        out = self.run_j("context", stdin=json.dumps({"cwd": str(self.proj)})).stdout
        self.assertIn("No journal here yet", out)
        self.assertFalse((self.proj / ".journal").exists())

    def test_projectless_goes_global(self):
        out = self.run_j("where", cwd=tempfile.gettempdir()).stdout.strip()
        self.assertEqual(Path(out), self.global_dir)

    def test_save_small_and_refuse_large(self):
        small = self.tmp / "helper.py"
        small.write_text("print(1)\n", encoding="utf-8")
        self.assertEqual(self.run_j("save", str(small)).returncode, 0)
        self.assertTrue((self.proj / ".journal" / "scripts" / "helper.py").exists())
        self.assertEqual(self.run_j("save", str(small), "--data", "--name", "d.py").returncode, 0)
        self.assertTrue((self.proj / ".journal" / "data" / "d.py").exists())
        big = self.tmp / "big.bin"
        big.write_bytes(b"0" * (1024 * 1024 + 1))
        r = self.run_j("save", str(big), "--data")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.proj / ".journal" / "data" / "big.bin").exists())

    @unittest.skipUnless(BASH, "bash not available")
    def test_hook_command_runs(self):
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        env = dict(self.env, CLAUDE_PLUGIN_ROOT=ROOT.as_posix())
        r = subprocess.run([BASH, "-c", cmd], input=json.dumps({"cwd": str(self.proj)}), cwd=str(self.proj),
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, f"bash={BASH}\nstdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("[journal] dir:", r.stdout)


if __name__ == "__main__":
    unittest.main()
