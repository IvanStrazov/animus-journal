# Changelog

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
