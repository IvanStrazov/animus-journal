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
        self.claude = self.tmp / "claude"
        self.env = dict(os.environ, JOURNAL_GLOBAL_DIR=str(self.global_dir), PYTHONIOENCODING="utf-8",
                        CLAUDE_CONFIG_DIR=str(self.claude))

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

    def test_amend_last_entry_updates_log_and_index(self):
        self.add("First", "task-a", "Done: one")
        self.add("Secnod tpyo", "task-b,api", "Done: two")
        r = self.run_j("amend", "--title", "Second, fixed")
        self.assertEqual(r.returncode, 0, r.stderr)
        j = self.proj / ".journal"
        log = next((j / "log").glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("#task-b #api — Second, fixed\nDone: two", log)
        self.assertIn("#task-a — First\nDone: one", log)
        self.assertNotIn("tpyo", log)
        idx = (j / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| #task-b #api | Second, fixed", idx)
        self.assertNotIn("tpyo", idx)
        r = self.run_j("amend", "--tags", "task-c", "--body", stdin="Done: rewritten")
        self.assertEqual(r.returncode, 0, r.stderr)
        log = next((j / "log").glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("#task-c — Second, fixed\nDone: rewritten", log)
        self.assertNotIn("Done: two", log)
        self.assertIn("| #task-c | Second, fixed", (j / "INDEX.md").read_text(encoding="utf-8"))

    def test_no_nested_journal_inside_a_journal(self):
        self.add("First", "task-a", "Done: one")
        inner = self.proj / ".journal" / "data"
        inner.mkdir(parents=True, exist_ok=True)
        r = self.run_j("add", "--title", "From inside", "--tags", "task-a", stdin="Done: two", cwd=inner)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((inner / ".journal").exists())
        self.assertIn("From inside", (self.proj / ".journal" / "INDEX.md").read_text(encoding="utf-8"))

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

    def test_ecosystem_link_offer_and_digest(self):
        ctx = lambda: self.run_j("context", stdin=json.dumps({"cwd": str(self.proj)})).stdout
        self.assertNotIn("animus-portrait", ctx())  # portrait not installed: no offer
        eco_file = self.claude / "ecosystem.json"
        self.assertIn("journal.py", json.loads(eco_file.read_text(encoding="utf-8"))["plugins"]["animus-journal"]["cmd"])
        portrait = self.tmp / "portrait.md"
        portrait.write_text("# P\n## Who\n- dev\n## Projects\n- bot\n"
                            "## Communication & preferences\n- Russian, direct\n- short answers\n",
                            encoding="utf-8")
        eco = json.loads(eco_file.read_text(encoding="utf-8"))
        eco["plugins"]["animus-portrait"] = {"cmd": "py portrait.py", "portrait_file": str(portrait)}
        eco_file.write_text(json.dumps(eco), encoding="utf-8")
        self.assertIn("not linked yet", ctx())
        self.assertEqual(self.run_j("link", "off").returncode, 0)
        out = ctx()
        self.assertNotIn("not linked yet", out)
        self.assertNotIn("Russian", out)
        self.run_j("link", "on")
        out = ctx()
        self.assertIn("- Russian, direct", out)
        self.assertIn("- dev", out)          # default digest: Communication + Who
        self.assertNotIn("- bot", out)       # Projects is not in the digest
        self.assertLess(out.index("Russian"), out.index("- dev"))
        self.assertIn("P = py portrait.py", out)
        self.assertIn("Projects, Communication & preferences", out)

    def test_broken_ecosystem_file_never_breaks_context(self):
        self.claude.mkdir(parents=True, exist_ok=True)
        (self.claude / "ecosystem.json").write_text("{not json", encoding="utf-8")
        r = self.run_j("context", stdin=json.dumps({"cwd": str(self.proj)}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[journal] dir:", r.stdout)

    def test_non_ascii_git_root(self):
        if not shutil.which("git"):
            self.skipTest("git not available")
        proj = self.tmp / "Проект по умолчанию" / "bot"
        proj.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(proj.parent)], capture_output=True)
        out = self.run_j("where", cwd=proj).stdout.strip()
        self.assertEqual(Path(out).resolve(), (proj.parent / ".journal").resolve())

    @unittest.skipUnless(BASH, "bash not available")
    def test_hook_command_runs(self):
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        env = dict(self.env, CLAUDE_PLUGIN_ROOT=ROOT.as_posix())
        r = subprocess.run([BASH, "-c", cmd], input=json.dumps({"cwd": str(self.proj)}), cwd=str(self.proj),
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, f"bash={BASH}\nstdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("[journal] dir:", r.stdout)

    def transcript(self, *tool_uses):
        t = self.tmp / "t.jsonl"
        lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})]
        for name, inp in tool_uses:
            lines.append(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "x", "name": name, "input": inp}]}}))
        t.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return t

    def stop(self, t, **extra):
        r = self.run_j("stop", stdin=json.dumps(dict({"transcript_path": str(t), "cwd": str(self.proj)}, **extra)))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_stop_silent_without_work(self):
        t = self.transcript(("Read", {"file_path": "a.py"}), ("Bash", {"command": "git status"}),
                            ("Edit", {"file_path": "a.py"}))
        self.assertIsNone(self.stop(t))

    def test_stop_nudges_after_commit_and_edits(self):
        out = self.stop(self.transcript(("Bash", {"command": "git add -A && git -C repo commit -m x"})))
        self.assertEqual(out["decision"], "block")
        self.assertIn("journal.py", out["reason"])
        edits = [("Edit", {"file_path": f"f{i}.py"}) for i in range(3)]
        self.assertEqual(self.stop(self.transcript(*edits))["decision"], "block")

    def test_stop_quiet_after_record_until_new_work(self):
        work = ("Bash", {"command": "git push origin main"})
        rec = ("Bash", {"command": '"py" "/x/journal.py" add --title T <<EOF\nDone: git commit\nEOF'})
        self.assertIsNone(self.stop(self.transcript(work, rec)))
        self.assertIsNone(self.stop(self.transcript(work, ("Bash", {"command": "py journal.py skip"}))))
        self.assertIsNotNone(self.stop(self.transcript(work, rec, work)))

    def test_stop_ignores_journal_and_memory_edits_and_loops(self):
        t = self.transcript(*[("Write", {"file_path": p}) for p in
                              ("C:\\p\\.journal\\x.md", "/home/u/.claude/projects/p/memory/a.md", "MEMORY.md")])
        self.assertIsNone(self.stop(t))
        busy = self.transcript(("Bash", {"command": "git commit -m x"}))
        self.assertIsNone(self.stop(busy, stop_hook_active=True))
        self.assertIsNone(self.run_j("stop", stdin="not json").stdout.strip() or None)
        off = dict(self.env, JOURNAL_NUDGE_EDITS="0")
        r = self.run_j("stop", stdin=json.dumps({"transcript_path": str(busy)}), env=off)
        self.assertEqual(r.stdout.strip(), "")

    def test_stop_hook_command_runs(self):
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        cmd = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
        env = dict(self.env, CLAUDE_PLUGIN_ROOT=ROOT.as_posix())
        t = self.transcript(("Bash", {"command": "git commit -m x"}))
        r = subprocess.run([BASH, "-c", cmd], input=json.dumps({"transcript_path": str(t)}), cwd=str(self.proj),
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_legacy_ecosystem_names_are_migrated(self):
        self.claude.mkdir(parents=True, exist_ok=True)
        portrait = self.tmp / "portrait.md"
        portrait.write_text("## Communication & preferences\n- legacy digest line\n", encoding="utf-8")
        legacy = {"plugins": {"claude-portrait": {"cmd": "py portrait.py", "portrait_file": str(portrait)}},
                  "links": {"claude-journal+claude-portrait": {
                      "enabled": True, "digest_sections": ["Communication & preferences"], "digest_lines": 5,
                      "auto_sections": ["Projects"]}}}
        (self.claude / "ecosystem.json").write_text(json.dumps(legacy), encoding="utf-8")
        out = self.run_j("context", stdin=json.dumps({"cwd": str(self.proj)})).stdout
        self.assertIn("- legacy digest line", out)
        self.assertIn("P = py portrait.py", out)
        eco = json.loads((self.claude / "ecosystem.json").read_text(encoding="utf-8"))
        self.assertIn("animus-journal+animus-portrait", eco["links"])
        self.assertNotIn("claude-portrait", eco["plugins"])

if __name__ == "__main__":
    unittest.main()
