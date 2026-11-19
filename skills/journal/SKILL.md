---
name: journal
description: Minimal project journal with a hard token budget — record what a session did and the project's current state, keep small helper scripts/data with the project, and look up past work on one task by its tag. Use proactively, without being asked — right after a milestone (commit, push, release, a verified fix, a decision) and at wrap-up of substantive work — and on /journal, "write this to the journal", "what did we do on X", or in Russian — «запиши в журнал», «занеси в журнал», «что мы делали по X», «когда мы это чинили». For an overview across all projects, use brief instead.
---

# Journal

All reads and writes go through one script. Never Read/Edit journal files directly — that is what costs tokens.

`J` below = the `cmd:` shown in the `[journal]` line injected at session start (an interpreter + `journal.py` path). Paste it as is in front of the subcommand, e.g. `"C:\…\python.exe" "C:\…\journal.py" find auth` — don't put it into a shell variable (the two quoted parts break). If that line is missing, take the `animus-journal` `cmd` from `~/.claude/ecosystem.json`; failing that, the script is `scripts/journal.py` in this plugin's root (`python` + forward slashes on Windows).

Location is automatic: `<project root>/.journal/` (git root, else cwd), or `~/journal/` for sessions with no project (home dir, temp dir, throwaway workspaces). The journal ships its own `.gitignore` (`*`), so it is never committed. When the user asks where the journal is or what is in it, `J where` prints the folder; describe the layout from this paragraph (`log/` by month, `INDEX.md`, `STATE.md`, `scripts/`, `data/`) instead of listing or opening the files.
There is no delete: entries are history. Never rm anything inside a journal folder, and don't offer to delete or "clean up" entries; if one is wrong, `amend` it (newest only) or add a correcting entry.

## Starting work
The SessionStart hook already injected STATE.md + the last 5 index lines. Don't re-read them.
To recall a task: `J find <tag or word> [more words]` → the 3 newest matching entries, printed exactly as stored (`--n N`, `--all`). If the user doubts it, say that this is the stored text — don't open the log to "double-check". `J tags` lists tags cheaply. Use `--all` only when asked.

## Recording (after milestones and at wrap-up, one Bash call each)
Record on your own initiative — the user often forgets to ask at the end. Do it right after a milestone (commit, push, release, a fix verified, a decision made) and again at wrap-up if more happened since. Only for real work: files changed, something configured or set up, a problem solved or diagnosed, a decision made. Skip quick Q&A and explanations; when unsure, record a short entry rather than asking.
Later records in the same session on the same task: `J amend --body` the newest entry with the merged facts instead of adding near-duplicates; a different task gets its own `add`.
A Stop hook (`J stop`) checks each finished turn: if work since the last `add`/`amend`/`skip` is unrecorded, it asks you to record it. Then record (or `J skip` when it really is not worth recording) and close with one short line — don't repeat the answer.
If the user says "start recording" at the beginning, don't write a placeholder entry: say you will record after the first milestone. Write entries and STATE in the user's language (field labels like `Done:` stay as they are). If the project goal is not known, ask instead of inventing one.

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
- A session that worked on two unrelated tasks gets one entry per task (each with its own task slug).
- To fix the newest entry (typo, wrong tag, missing fact): `J amend --title "…"` / `--tags a,b` / `--body` (new body from stdin), combined into one call. Older entries are history: add a new entry instead of rewriting them. To see an entry, use `J find`, never grep/cat the log.

If the start-of-session context has a `[journal] portrait linked: P = …` line, then after `add`, and only if this session showed something new for them, update just the sections that line names (never sensitive topics, never other sections), from this session alone:
`P show --section "<name>"`, then `P save --section "<name>"` with the whole merged section (≤ 20 lines). Skip it when nothing changed: that is the usual case.
If the context says animus-portrait is installed and not linked yet, mention it once, in one short line at the end of the reply in which you recorded an entry (never in Q&A sessions or mid-task); the `portrait` skill sets the link up.

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
STATE is a snapshot, not history: keep `Goal:` always, drop finished or obsolete items. To show the current STATE to the user, run `J context` (it prints STATE and the latest entries).

## Keeping files
Reusable helper scripts or small data (≤ 1 MB) made during work: write the file anywhere outside the journal (e.g. a scratch/temp dir), then copy it in with `save` — never write into the journal folder yourself:
`J save <file>` → `.journal/scripts/`, `J save <file> --data` → `.journal/data/` (`--name` renames). Larger files are refused: put their path in the entry. Mention saved files on the entry's Done line. Code that belongs to the project goes in the project, not here.
