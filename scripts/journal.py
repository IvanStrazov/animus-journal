#!/usr/bin/env python3
"""claude-journal: a minimal, token-budgeted project journal for Claude Code.

Layout (in <project>/.journal/, or the global dir for sessions with no project):
  STATE.md          current project snapshot, overwritten, <= STATE_MAX lines
  INDEX.md          one line per session: date | #tags | title
  log/YYYY-MM.md    entries, appended, one "## " section per session
  scripts/  data/   helper scripts and small data files kept with the project
  .gitignore        "*"  -> the journal never gets committed

Commands:
  context                         SessionStart hook: print STATE + last index lines
  add --title T [--tags a,b]      entry body from stdin -> log + INDEX
  state                           stdin -> STATE.md
  find TERM... [--n N] [--all]    matching entries, newest first
  tags                            tag counts
  save FILE [--data] [--name N]   copy a small file into scripts/ or data/
  where                           print the journal dir

Budgets can be changed with env vars: JOURNAL_STATE_MAX, JOURNAL_ENTRY_MAX,
JOURNAL_INDEX_TAIL, JOURNAL_SAVE_MAX_KB. JOURNAL_GLOBAL_DIR sets the global dir.
Standard library only, Python 3.8+.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


STATE_MAX = _int_env("JOURNAL_STATE_MAX", 40)
ENTRY_MAX = _int_env("JOURNAL_ENTRY_MAX", 20)
INDEX_TAIL = _int_env("JOURNAL_INDEX_TAIL", 5)
SAVE_MAX_BYTES = _int_env("JOURNAL_SAVE_MAX_KB", 1024) * 1024
GLOBAL_DIR = Path(os.environ.get("JOURNAL_GLOBAL_DIR") or Path.home() / "journal").expanduser()
SCRIPT = Path(__file__).resolve()

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _is_projectless(p: Path) -> bool:
    """Home dir, temp dir, or an app-created throwaway workspace."""
    s = str(p).replace("\\", "/").lower()
    if "scratch-workspaces" in s:
        return True
    for base in (Path.home(), Path(tempfile.gettempdir())):
        try:
            if p == base.resolve():
                return True
        except Exception:
            pass
    return False


def project_root(cwd: str):
    p = Path(cwd).resolve()
    if _is_projectless(p):
        return None
    try:
        top = subprocess.run(["git", "-C", str(p), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if top:
            return Path(top)
    except Exception:
        pass
    return p


def journal_dir(cwd: str) -> Path:
    root = project_root(cwd)
    return GLOBAL_DIR if root is None else root / ".journal"


def ensure(j: Path) -> Path:
    (j / "log").mkdir(parents=True, exist_ok=True)
    gi = j / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")
    return j


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def cap(lines, n, what):
    if len(lines) > n:
        print(f"[journal] {what} trimmed to {n} lines (was {len(lines)})", file=sys.stderr)
        return lines[:n]
    return lines


def cmd_context(args):
    cwd = os.getcwd()
    try:
        data = json.loads(sys.stdin.read() or "{}")
        cwd = data.get("cwd") or cwd
    except Exception:
        pass
    j = journal_dir(cwd)
    is_global = j == GLOBAL_DIR
    cmd = f'"{sys.executable}" "{SCRIPT}"'
    out = [f"[journal] dir: {j}  cmd: {cmd}"]
    if not j.exists():
        out.append("No journal here yet. Record substantive work at wrap-up with the `journal` skill.")
    else:
        state = read(j / "STATE.md").strip()
        if state and not is_global:
            out.append(state)
        idx = [l for l in read(j / "INDEX.md").splitlines() if l.strip()]
        if idx:
            out.append("Recent sessions:")
            out += idx[-INDEX_TAIL:]
        out.append("More: `find <tag|word>`. Record at wrap-up with the `journal` skill.")
    print("\n".join(out))


def cmd_add(args):
    j = ensure(journal_dir(os.getcwd()))
    body = [l.rstrip() for l in sys.stdin.read().strip().splitlines()]
    body = cap(body, ENTRY_MAX, "entry")
    now = dt.datetime.now()
    tags = " ".join("#" + t.strip().lstrip("#") for t in (args.tags or "").split(",") if t.strip())
    title = " ".join(args.title.split())
    head = " ".join(x for x in (f"## {now:%Y-%m-%d %H:%M}", tags, "—", title) if x)
    log = j / "log" / f"{now:%Y-%m}.md"
    sep = "\n" if log.exists() and log.stat().st_size else ""
    with log.open("a", encoding="utf-8") as f:
        f.write(sep + head + "\n" + "\n".join(body) + "\n")
    with (j / "INDEX.md").open("a", encoding="utf-8") as f:
        f.write(f"{now:%Y-%m-%d} | {tags or '-'} | {title}\n")
    print(f"[journal] entry added -> {log}")


def cmd_state(args):
    j = ensure(journal_dir(os.getcwd()))
    lines = cap(sys.stdin.read().strip().splitlines(), STATE_MAX, "STATE")
    (j / "STATE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[journal] STATE.md updated ({len(lines)} lines)")


def entries(j: Path):
    for log in sorted((j / "log").glob("*.md")):
        for sec in re.split(r"(?m)^(?=## )", read(log)):
            if sec.startswith("## "):
                yield sec.strip()


def cmd_find(args):
    j = journal_dir(os.getcwd())
    terms = [t.lower().lstrip("#") for t in args.terms]
    hits = [e for e in entries(j) if all(t in e.lower() for t in terms)]
    hits.reverse()
    if not args.all:
        hits = hits[:args.n]
    print("\n\n".join(hits) if hits else "[journal] nothing found")


def cmd_tags(args):
    j = journal_dir(os.getcwd())
    counts = {}
    for l in read(j / "INDEX.md").splitlines():
        for t in re.findall(r"#[^\s|#]+", l):
            counts[t] = counts.get(t, 0) + 1
    print(" ".join(f"{t}({n})" for t, n in sorted(counts.items(), key=lambda x: -x[1])) or "[journal] no tags")


def cmd_save(args):
    src = Path(args.file)
    if not src.is_file():
        sys.exit(f"[journal] not a file: {src}")
    size = src.stat().st_size
    if size > SAVE_MAX_BYTES:
        sys.exit(f"[journal] {src.name} is {size // 1024} KB > {SAVE_MAX_BYTES // 1024} KB; "
                 "not copied - mention its path in the entry instead")
    j = ensure(journal_dir(os.getcwd()))
    dest_dir = j / ("data" if args.data else "scripts")
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / (args.name or src.name)
    shutil.copy2(src, dest)
    print(f"[journal] saved -> {dest}")


def cmd_where(args):
    print(journal_dir(os.getcwd()))


def main():
    ap = argparse.ArgumentParser(prog="journal.py", description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("context").set_defaults(f=cmd_context)
    a = sp.add_parser("add"); a.add_argument("--title", required=True); a.add_argument("--tags")
    a.set_defaults(f=cmd_add)
    sp.add_parser("state").set_defaults(f=cmd_state)
    f = sp.add_parser("find"); f.add_argument("terms", nargs="+"); f.add_argument("--n", type=int, default=3)
    f.add_argument("--all", action="store_true"); f.set_defaults(f=cmd_find)
    sp.add_parser("tags").set_defaults(f=cmd_tags)
    s = sp.add_parser("save"); s.add_argument("file"); s.add_argument("--data", action="store_true")
    s.add_argument("--name"); s.set_defaults(f=cmd_save)
    sp.add_parser("where").set_defaults(f=cmd_where)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
