# Claude Session Register

Index of named Claude Code sessions and their checkpoints. One row per session. One file per session, `<session-name>.md`, the record of where that session's work stands. The Markdown is the record; the artifact is an HTML page rendered from it by `~/.claude/skills/checkpoint/render.py`, so every checkpoint page shares one design.

The checkpoint file is the source of truth. The artifact is a designed rendering of it on claude.ai. Git history here is the version history. The artifact keeps only recent publishes and its gallery listing is unreliable for dormant artifacts, so the URL in this table is how a resumed session finds its page.

Rules for what goes in a checkpoint live in `~/.claude/CLAUDE.md` under "Session Checkpoints". The template, section structure and page design, is in `_template/`. The `/checkpoint` skill writes the content; `_template/checkpoint.py` archives, renders, commits and pushes. Each session may also have `<session-name>.archive.md` holding items moved out of view.

Hooks read this table by exact session name in the first column. Keep the table format: one row per session, pipes, no merged cells.

| Session | Topic | Checkpoint | Artifact | Last checkpoint |
|---|---|---|---|---|
