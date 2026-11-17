# Contributing

Thanks for your interest! Issues and pull requests are welcome.

## The one rule: protect the token budget

animus-journal exists to keep context cost small and predictable. A change that adds tokens at session start, adds a hook that fires often (on every tool call or prompt), or adds a runtime dependency needs a strong reason. Say in the PR how it affects the numbers in the README's token budget table.

## Ground rules

- Standard library only, Python 3.9+.
- Must work on macOS, Linux and Windows (Git Bash).
- Journal files stay plain Markdown that a person can read and edit.
- Keep `skills/journal/SKILL.md` short: it is loaded into context every time the skill is used.

## Development

```bash
python -m unittest discover -s tests -v
```

CI runs the same tests on Ubuntu, macOS and Windows.

To try your working copy in Claude Code, add the local folder as a marketplace:

```
/plugin marketplace add /path/to/animus-journal
/plugin install animus-journal@animus-journal
```

## Pull requests

- One topic per PR, with a short description of what changed and why.
- Add or update a test in `tests/` for behavior changes.
- Add a line to `CHANGELOG.md` under an "Unreleased" heading.
