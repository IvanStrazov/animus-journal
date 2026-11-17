# Changelog

## 0.4.5 — 2026-11-17
- Skill: Russian trigger phrases; scoped to one task (the cross-project overview is brief).

## 0.4.4 — 2026-11-17
- Running a command from inside a journal folder (e.g. `~/journal/data`) now uses that journal instead of creating a nested `.journal`.
- `amend` without `--body` says when text on stdin was ignored.
- Skill: no placeholder entry on "start recording"; entries and STATE in the user's language; ask for an unknown goal; files go in via `save`, never rm inside a journal.

## 0.4.3 — 2026-11-17
- The session-start hint about linking animus-portrait now says: once, in one line, after recording an entry (never in Q&A).
- Skill: `find` prints entries exactly as stored, no need to open the log; fallback to the `cmd` in ecosystem.json when the start-of-session line is missing.

## 0.4.2 — 2026-11-17
- Skill: a session with two unrelated tasks gets one entry per task; STATE always keeps `Goal:`; `context` shows the current STATE.

## 0.4.1 — 2026-11-17
- Skill: paste the `cmd:` in front of the subcommand (a shell variable breaks the two quoted parts).
- Skill: answer "where is the journal / what is in it" with `where` and the layout, not by opening files; there is no delete — don't offer to clean up entries.
- Skill: clearer "real work" rule for recording; one `amend` call; the portrait hint only after an entry was recorded.

## 0.4.0 — 2026-11-17
- New `amend [--title T] [--tags a,b] [--body]`: fix the newest entry; the log section and its INDEX line change together (no more hand edits that leave INDEX stale).
- Skill: older entries are history (add a new one instead of rewriting); look at entries with `find`, never grep/cat the log; the portrait-link hint is one short line at the end of a wrap-up.

## 0.3.1 — 2026-11-17

- Fix: project paths with non-ASCII characters (e.g. Cyrillic) were mis-decoded on Windows, so the journal could resolve to the wrong folder.

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
