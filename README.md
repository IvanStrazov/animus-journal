# animus-journal

[![tests](https://github.com/IvanStrazov/animus-journal/actions/workflows/test.yml/badge.svg)](https://github.com/IvanStrazov/animus-journal/actions/workflows/test.yml)
[![version](https://img.shields.io/badge/version-0.3.1-blue)](CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)
![python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)

**A minimal project journal for Claude Code, on a hard token budget.**

> **Part of Animus** — small, local, token-frugal plugins that let Claude Code remember you and your work. Each works alone; together they share context through `~/.claude/ecosystem.json`.
>
> | Plugin | What it does |
> |---|---|
> | [animus-journal](https://github.com/IvanStrazov/animus-journal) | Project journal on a hard token budget: what was done, decided, next |
> | [animus-portrait](https://github.com/IvanStrazov/animus-portrait) | A compact portrait of you, built from your own sessions |
> | [animus-brief](https://github.com/IvanStrazov/animus-brief) | One status brief across all your projects |
> | [animus-limits](https://github.com/IvanStrazov/animus-limits) | Token spend per task, per-task limits, cost estimates |
> | [animus-relay](https://github.com/IvanStrazov/animus-relay) | Hand work over to a fresh session without losing the thread |
> | [animus-review](https://github.com/IvanStrazov/animus-review) | Send work to another model for review, triage the answer |
>
> The name nods to the memory machine from Assassin's Creed and to the Latin *animus*, "mind". Not affiliated with Ubisoft.

Most memory plugins record everything and pay for it in context. animus-journal does the opposite: it keeps a short, human-readable journal and keeps the cost low with limits enforced in code, not just in the prompt.

- **≤ 40-line project snapshot** (`STATE.md`) + the last 5 session lines are injected at session start. That's all.
- **≤ 20 lines per session entry**, written in a single shell call after milestones and at wrap-up — without you having to ask.
- **Lookup by task tag**: `find <tag>` returns only the 3 newest matching entries, not the whole history.
- **No hooks on every tool call or prompt.** A `SessionStart` hook injects the context; a `Stop` hook stays silent unless the session did work (a commit/push, or 3+ file edits) since the last record, and then asks Claude to record it. `JOURNAL_NUDGE_EDITS=0` turns the reminder off.
- **One stdlib Python file + plain Markdown.** No database, no vector store, no background process, no network, no extra model calls.

## Token budget (measured)

| Moment | What enters context | Worst case |
|---|---|---|
| Session start | `STATE.md` (≤ 40 lines) + 5 index lines | ~3.3 KB ≈ 800 tokens |
| Recording | the entry you write (≤ 20 lines) + a one-line ack | ≈ 150–300 tokens |
| Recalling a task | 3 matching entries | ≈ 200–1 000 tokens |
| Skill instructions | loaded only when the skill is used | ~2.4 KB ≈ 600 tokens |

Limits can be changed with environment variables: `JOURNAL_STATE_MAX`, `JOURNAL_ENTRY_MAX`, `JOURNAL_INDEX_TAIL`, `JOURNAL_SAVE_MAX_KB`, `JOURNAL_NUDGE_EDITS` (edits that trigger the Stop reminder, default 3, `0` = off).

## What it stores

```
<project>/.journal/
  STATE.md         current snapshot: goal, done, in progress, open questions, next steps
  INDEX.md         one line per session: date | #tags | title
  log/2026-11.md   session entries, one "## " section each
  scripts/ data/   helper scripts and small data files (≤ 1 MB) kept with the project
  .gitignore       "*" — the journal stays local and is never committed
```

Sessions without a project (home dir, temp dir, throwaway workspaces) go to a shared `~/journal/` (override with `JOURNAL_GLOBAL_DIR`).

An entry looks like this:

```
## 2026-11-16 19:47 #parser #api — Switched log parser to regex
Goal: parse nginx logs without the json module
Done: src/parse.py, tests/test_parse.py; commit 3f2a1c
Decided: regex over json — logs are not valid JSON
Next: handle multi-line stack traces
```

## Install

```
/plugin marketplace add IvanStrazov/animus-journal
/plugin install animus-journal@animus-journal
```

Requires Python 3.9+ on `PATH` (`python3` or `python`). Works on macOS, Linux and Windows (Git Bash, which Claude Code uses on Windows).

## Use

You mostly don't have to do anything:

- At session start Claude sees the snapshot and recent sessions.
- At the end of substantive work Claude records an entry and updates the snapshot. You can also ask: `/journal` or "write this to the journal".
- Ask "what did we do on the parser?" — Claude runs `find parser`.

Commands (Claude runs them; you can too): `add`, `state`, `find`, `tags`, `save`, `where`, `link` — see `python scripts/journal.py -h`.

## Works with animus-portrait (optional)

If [animus-portrait](https://github.com/IvanStrazov/animus-portrait) is installed, the journal offers to link the two, once. Nothing changes until you agree (`journal.py link on`, or say yes in the `portrait` skill).

When linked, the plugins share `~/.claude/ecosystem.json`:
- **Session start** adds a short digest of your portrait (default: Communication + Who, ≤ 15 lines). `portrait.py digest-cost` shows what each size costs you with prompt caching.
- **At wrap-up** the journal updates only the portrait's *Projects* and *Communication & preferences* sections from that session, and only when something changed. Sensitive topics are never touched.

`journal.py link off` undoes it. A missing or broken `ecosystem.json` never breaks session start.

## How it compares

If you want automatic capture of every action with semantic search, use a full memory system such as claude-mem. animus-journal is for people who want a small, readable log they control, with a predictable and low context cost.

## License

MIT
