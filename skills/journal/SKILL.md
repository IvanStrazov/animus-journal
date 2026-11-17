---
name: journal
description: Minimal project journal with a hard token budget — record what a session did and the project's current state, keep small helper scripts/data with the project, and look up past work by task tag. Use at wrap-up of substantive work, on /journal or "write this to the journal", or when asked what was done earlier on a task.
---

# Journal

All reads and writes go through one script. Never Read/Edit journal files directly — that is what costs tokens.

`J` below = the `cmd:` shown in the `[journal]` line injected at session start (an interpreter + `journal.py` path). If that line is missing, the script is `scripts/journal.py` in this plugin's root.

Location is automatic: `<project root>/.journal/` (git root, else cwd), or `~/journal/` for sessions with no project (home dir, temp dir, throwaway workspaces). The journal ships its own `.gitignore` (`*`), so it is never committed.

## Starting work
The SessionStart hook already injected STATE.md + the last 5 index lines. Don't re-read them.
To recall a task: `J find <tag or word> [more words]` → the 3 newest matching entries (`--n N`, `--all`). `J tags` lists tags cheaply. Use `--all` only when asked.

## Recording (at wrap-up, one Bash call)
Only when the session did real work (changes, decisions, findings). Skip quick Q&A.

```bash
J add --title "Short result-oriented title" --tags task-slug,area <<'EOF'
Goal: ...
Done: ... (files, commits)
Decided: X because Y
Dead ends: ...
Next: ...
EOF
```
- ≤ 20 lines, facts only: no logs, no code, no retelling the conversation. Omit empty fields.
- 1–3 lowercase kebab tags; reuse existing ones (`J tags`). The first tag is the task slug — the key for `find`.
- In `~/journal/` the first tag names the topic.

If the start-of-session context has a `[journal] portrait linked: P = …` line, then after `add`, and only if this session showed something new for them, update just the sections that line names (never sensitive topics, never other sections), from this session alone:
`P show --section "<name>"`, then `P save --section "<name>"` with the whole merged section (≤ 20 lines). Skip it when nothing changed: that is the usual case.
If the context says animus-portrait is installed and not linked yet, mention it once; the `portrait` skill sets the link up.

In a project, when the picture changed, rewrite the snapshot (≤ 40 lines, whole file):
```bash
J state <<'EOF'
# <project> — state
Goal: ...
Done: ...
In progress: ...
Open questions: ...
Next steps: ...
Key files: path — role
EOF
```
STATE is a snapshot, not history: drop finished or obsolete items.

## Keeping files
Reusable helper scripts or small data (≤ 1 MB) made during work, e.g. in a scratch/temp dir:
`J save <file>` → `.journal/scripts/`, `J save <file> --data` → `.journal/data/` (`--name` renames). Larger files are refused: put their path in the entry. Mention saved files on the entry's Done line. Code that belongs to the project goes in the project, not here.
