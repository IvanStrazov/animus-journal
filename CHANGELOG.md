# Changelog

## 0.2.0 — 2026-11-17

- Link with [claude-portrait](https://github.com/IvanStrazov/claude-portrait) through a shared `~/.claude/ecosystem.json`, only after the user agrees (`link on|off`).
- When linked: session start adds a short portrait digest (default: Communication + Who, ≤ 15 lines), and at wrap-up the journal updates only the portrait's Projects and Communication sections.
- Unlinked or without claude-portrait, the output is unchanged apart from a one-line offer when claude-portrait is installed.

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
