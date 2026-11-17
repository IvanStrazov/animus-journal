# Changelog

## 0.3.0 — 2026-11-17

- Renamed to **animus-journal**, part of the [Animus](https://github.com/IvanStrazov/animus-portrait#animus) ecosystem (was claude-journal). New repository: `IvanStrazov/animus-journal` (the old `IvanStrazov/claude-journal` stays as 0.2.0).
- To upgrade from 0.2.0: `/plugin marketplace add IvanStrazov/animus-journal`, then `/plugin install animus-journal@animus-journal`, then remove `claude-journal`. Your journals are untouched.
- The shared `~/.claude/ecosystem.json` is migrated automatically: an existing link with the portrait carries over.

## 0.2.0 — 2026-11-17

- Link with [animus-portrait](https://github.com/IvanStrazov/animus-portrait) through a shared `~/.claude/ecosystem.json`, only after the user agrees (`link on|off`).
- When linked: session start adds a short portrait digest (default: Communication + Who, ≤ 15 lines), and at wrap-up the journal updates only the portrait's Projects and Communication sections.
- Unlinked or without animus-portrait, the output is unchanged apart from a one-line offer when animus-portrait is installed.

## 0.1.0 — 2026-11-16

First release.

- `journal` skill and a single `SessionStart` hook.
- Session start injects `STATE.md` (≤ 40 lines) and the last 5 index lines, ~800 tokens at most.
- `add`: session entries of ≤ 20 lines, written in one shell call.
- `state`: rewrites the project snapshot (≤ 40 lines).
- `find`: the 3 newest entries matching a tag or words; `tags`: tag counts.
- `save`: keeps helper scripts and data files (≤ 1 MB) in `.journal/scripts/` and `.journal/data/`.
- Journal lives in `<project>/.journal/` with its own `.gitignore`; sessions with no project use `~/journal/`.
- Limits configurable with `JOURNAL_*` environment variables.
