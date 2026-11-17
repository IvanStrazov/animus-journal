#!/usr/bin/env python3
"""animus-journal: a minimal, token-budgeted project journal for Claude Code.

Layout (in <project>/.journal/, or the global dir for sessions with no project):
  STATE.md          current project snapshot, overwritten, <= STATE_MAX lines
  INDEX.md          one line per session: date | #tags | title
  log/YYYY-MM.md    entries, appended, one "## " section per session
  scripts/  data/   helper scripts and small data files kept with the project
  .gitignore        "*"  -> the journal never gets committed

Commands:
  context                         SessionStart hook: print STATE + last index lines
  add --title T [--tags a,b]      entry body from stdin -> log + INDEX
  amend [--title T] [--tags a,b] [--body]   fix the LAST entry (log + INDEX); --body: new body from stdin
  state                           stdin -> STATE.md
  find TERM... [--n N] [--all]    matching entries, newest first
  tags                            tag counts
  save FILE [--data] [--name N]   copy a small file into scripts/ or data/
  where                           print the journal dir
  link on|off                     link with animus-portrait via ~/.claude/ecosystem.json

Budgets can be changed with env vars: JOURNAL_STATE_MAX, JOURNAL_ENTRY_MAX,
JOURNAL_INDEX_TAIL, JOURNAL_SAVE_MAX_KB. JOURNAL_GLOBAL_DIR sets the global dir.
CLAUDE_ECOSYSTEM_FILE moves the shared links file (default ~/.claude/ecosystem.json).
Standard library only, Python 3.9+.
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
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()

# Ecosystem: links with sibling plugins (shared file, same schema in each plugin).
ECO_FILE = Path(os.environ.get("CLAUDE_ECOSYSTEM_FILE") or CLAUDE_DIR / "ecosystem.json").expanduser()
SELF, PEER = "animus-journal", "animus-portrait"
LINK = "+".join(sorted((SELF, PEER)))
# Names before the Animus rename (<= 0.2.0); entries under them are migrated on load.
LEGACY_NAMES = {"claude-journal": "animus-journal", "claude-portrait": "animus-portrait"}
LEGACY_LINK = "claude-journal+claude-portrait"
LINK_DEFAULTS = {"auto_sections": ["Projects", "Communication & preferences"],
                 "digest_sections": ["Communication & preferences", "Who"], "digest_lines": 15}

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
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5).stdout.strip()
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


def eco_load():
    try:
        e = json.loads(ECO_FILE.read_text(encoding="utf-8"))
        if not isinstance(e, dict):
            e = {}
    except (OSError, ValueError):
        e = {}
    e.setdefault("version", 1)
    e.setdefault("plugins", {})
    e.setdefault("links", {})
    for old, new in LEGACY_NAMES.items():
        if old in e["plugins"]:
            e["plugins"].setdefault(new, e["plugins"].pop(old))
    if LEGACY_LINK in e["links"]:
        e["links"].setdefault(LINK, e["links"].pop(LEGACY_LINK))
    return e


def eco_write(e):
    ECO_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(ECO_FILE.parent), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(e, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, ECO_FILE)


def eco_register():
    """Record where this plugin's script is, so sibling plugins can find it."""
    e = eco_load()
    me = {"cmd": f'"{sys.executable}" "{SCRIPT}"'}
    if e["plugins"].get(SELF) != me:
        e["plugins"][SELF] = me
        try:
            eco_write(e)
        except OSError:
            pass
    return e


def peer_installed(e):
    cache = CLAUDE_DIR / "plugins" / "cache"
    old = [k for k, v in LEGACY_NAMES.items() if v == PEER]
    return PEER in e["plugins"] or any((cache / n).is_dir() for n in [PEER] + old)


def portrait_digest(peer, link):
    """Non-empty lines of the chosen portrait sections, in the chosen order, capped in total."""
    names = [s.strip().lower() for s in link.get("digest_sections") or [] if s.strip()]
    n = int(link.get("digest_lines") or 0)
    if not names or n <= 0:
        return []
    try:
        text = Path(peer.get("portrait_file", "")).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return []
    found, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            head = line[3:].strip().lower()
            cur = next((s for s in names if head.startswith(s)), None)
            if cur is not None:
                found.setdefault(cur, [])
        elif cur is not None and line.strip():
            found[cur].append(line)
    lines = [l for s in names for l in found.get(s, [])]
    return lines[:n]


def ecosystem_lines():
    e = eco_register()
    if not peer_installed(e):
        return []
    link = e["links"].get(LINK)
    if link is None:
        return [f"[journal] {PEER} is installed and not linked yet. Offer the link once via the "
                "`portrait` skill (it shows digest sizes with their token cost)."]
    if not link.get("enabled"):
        return []
    peer = e["plugins"].get(PEER) or {}
    out = []
    digest = portrait_digest(peer, link)
    if digest:
        out.append("About the user (from the portrait):")
        out += digest
    if peer.get("cmd"):
        secs = ", ".join(link.get("auto_sections") or [])
        out.append(f"[journal] portrait linked: P = {peer['cmd']}; at wrap-up update only: {secs}.")
    return out


def cmd_link(args):
    e = eco_register()
    link = dict(LINK_DEFAULTS, **(e["links"].get(LINK) or {}))
    link["enabled"] = args.state == "on"
    link["decided"] = dt.date.today().isoformat()
    e["links"][LINK] = link
    eco_write(e)
    print(f"[journal] link {LINK}: {args.state}")


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
    try:
        out += ecosystem_lines()
    except Exception:
        pass  # a broken shared file must never break session start
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


def cmd_amend(args):
    """Fix the newest entry: title, tags and/or body. Rewrites that one section and its INDEX line."""
    j = journal_dir(os.getcwd())
    logs = sorted((j / "log").glob("*.md")) if (j / "log").is_dir() else []
    if not logs:
        sys.exit("[journal] nothing to amend")
    log = logs[-1]
    secs = re.split(r"(?m)^(?=## )", read(log))
    i = max((k for k, s in enumerate(secs) if s.startswith("## ")), default=None)
    if i is None:
        sys.exit("[journal] nothing to amend")
    head, _, rest = secs[i].partition("\n")
    m = re.match(r"## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})((?: #\S+)*)(?: —)? ?(.*)$", head.strip())
    if not m:
        sys.exit(f"[journal] cannot parse the last entry header: {head!r}")
    when, old_tags, old_title = m.group(1), m.group(2).strip(), m.group(3).strip()
    tags = old_tags if args.tags is None else " ".join(
        "#" + t.strip().lstrip("#") for t in args.tags.split(",") if t.strip())
    title = old_title if args.title is None else " ".join(args.title.split())
    body = rest.rstrip("\n")
    if args.body:
        body = "\n".join(cap([l.rstrip() for l in sys.stdin.read().strip().splitlines()], ENTRY_MAX, "entry"))
    if args.title is None and args.tags is None and not args.body:
        sys.exit("[journal] nothing to change: pass --title, --tags or --body")
    trail = "\n" if i < len(secs) - 1 else ""
    secs[i] = " ".join(x for x in (f"## {when}", tags, "—", title) if x) + "\n" + body + "\n" + trail
    log.write_text("".join(secs), encoding="utf-8")
    idx_f = j / "INDEX.md"
    idx = read(idx_f).splitlines()
    old_line = f"{when[:10]} | {old_tags or '-'} | {old_title}"
    k = max((n for n, l in enumerate(idx) if l.strip() == old_line), default=len(idx) - 1 if idx else None)
    if k is not None and k >= 0:
        idx[k] = f"{when[:10]} | {tags or '-'} | {title}"
        idx_f.write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(f"[journal] last entry amended -> {log}")
    print(" ".join(x for x in (f"## {when}", tags, "—", title) if x))


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
    m = sp.add_parser("amend"); m.add_argument("--title"); m.add_argument("--tags")
    m.add_argument("--body", action="store_true"); m.set_defaults(f=cmd_amend)
    sp.add_parser("state").set_defaults(f=cmd_state)
    f = sp.add_parser("find"); f.add_argument("terms", nargs="+"); f.add_argument("--n", type=int, default=3)
    f.add_argument("--all", action="store_true"); f.set_defaults(f=cmd_find)
    sp.add_parser("tags").set_defaults(f=cmd_tags)
    s = sp.add_parser("save"); s.add_argument("file"); s.add_argument("--data", action="store_true")
    s.add_argument("--name"); s.set_defaults(f=cmd_save)
    sp.add_parser("where").set_defaults(f=cmd_where)
    k = sp.add_parser("link"); k.add_argument("state", choices=("on", "off")); k.set_defaults(f=cmd_link)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
