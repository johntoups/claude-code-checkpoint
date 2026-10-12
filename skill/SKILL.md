---
name: checkpoint
description: Write this session's checkpoint (now, next step, waiting on, up next, recent sessions, topic, decisions, facts, traps), then run checkpoint.py to archive, render, commit and push, and publish the designed HTML artifact. Use on wrap-up phrases, on /checkpoint, and with --new <name> to register a session for the first time.
---

You are the CHECKPOINT skill. One file per named session lets a resumed session, and the user, pick the work back up without asking "where are we". You write content. `checkpoint.py` does all bookkeeping. Keep token use low: edit sections in place, never rewrite the whole file.

## Locations

- Register: `$CHECKPOINT_REGISTER`, default `~/claude-session-register/` (README.md is the index; a private git repo, or a folder inside one)
- Checkpoint: `<register>/<session-name>.md`; archive: `<session-name>.archive.md` (written by the helper, read only when a question needs it)
- Template, design and helper: `<register>/_template/` (`TEMPLATE.md`, `checkpoint.css`, `shell.html`, `render.py`, `checkpoint.py`, and `kinds/` for game checkpoints)
- Helper: `python3 ~/.claude/skills/checkpoint/checkpoint.py` (symlink)
- Render output: `<scratchpad>/checkpoint-render/` (your session's scratchpad directory)

## Session name

Use the name from the SessionStart hook's `[session-register] Session name:` line, or `grep '"type":"custom-title"' <transcript_path> | tail -1`. No name: ask the user. Never invent one. The helper refuses unsafe names and case-insensitive duplicates.

## Arguments

- `/checkpoint` — update this session's checkpoint.
- `/checkpoint --new <session-name>` — register it: `checkpoint.py new <name> "<one-line topic>"`, then fill the sections with one `patch` (use `section` for each template section), which also finishes.

## Steps

0. **Live twin check.** List peer sessions. If another running session has this name, tell the user before writing; two live sessions on one checkpoint interleave. Proceed only if he says so.
   **Only your own checkpoint.** `patch` and `finish` act on this session's name from the SessionStart hook. Writing another session's checkpoint (a migration, a sheet fill, a carried decision) needs the user's explicit go-ahead for that file. Then, in the same turn: list peer sessions, and if that session is running, stop and ask the user (its `finish` would commit your uncommitted edit with its own); run `git -C <register> status --short -- "<name>.md"` and `git -C <register> log -1 --format='%h %ad' -- "<name>.md"` so you build on its latest state; `patch` it, then `finish <name>` straight away so the change lands in its own commit; and add a References line naming this session and the date. `finish` stamps that checkpoint's time, so say so to the user.
1. **Don't re-read the checkpoint.** You read it at session start. Re-read only if it may have changed since (another session, the user, or a compaction), and never read the archive unless a question needs it. If it still has the old headings (Where we are, Last touched, Open items, Decisions made, Facts established, Pointers), or a project's `.claude/checkpoint.json` names a different kind than its header, migrate it now onto the right template: carry every decision, fact, unverified item and trap across verbatim, and say where each moved. Migration is the one case where a full rewrite is right.
2. **Write the changes in one `patch` call.** Put only what changed into one JSON spec and pipe it in. The helper applies all of it or none of it.
   ```bash
   python3 ~/.claude/skills/checkpoint/checkpoint.py patch <name> - --finish --out <scratchpad>/checkpoint-render <<'JSON'
   {"now": ["Two or three sentences of state."],
    "next": "The one concrete action that resumes the work.",
    "session": "What this session did today, one line (replaces today's line if there is one).",
    "add": {"Decisions": ["Decision, and why."], "Facts": ["Fact (source: ...)"], "Traps": ["..."],
            "Up next": ["..."], "Parked": ["Item, because why."], "Waiting on": ["**<your name>:** ..."],
            "Unverified": ["Belief. Check: what confirms it."], "References": ["..."]},
    "mark": [["Up next", "unique words from the item", "done"], ["Traps", "...", "obsolete"]],
    "edit": [["Facts", "unique words", "Replacement text for the whole item (source: ...)."]],
    "section": {"Topic": "**Purpose:** ...\n\n**Scope:** ...\n\n**Out of scope:** ..."}}
   JSON
   ```
   - Every key is optional. Decisions without a leading date get today's. Up next items are numbered for you. A `mark` or `edit` match must hit exactly one item; if it errors, nothing was written: fix the match and re-run.
   - Markers: `done` (Up next, Waiting on, Between games), `superseded` (Decisions, Table rulings), `obsolete` (Traps), `resolved` (Unverified, Threads), `pinned` (Facts: stays in view past the 15-fact cap).
   - Section rules: *Now* is two or three sentences plus **Next step:**, exactly one action. *Waiting on* bullets start `**<your name>:**`, `**External:**` or a named person; everything needing the user goes here. *Up next* is priority order, one sentence each. *Decisions* are never deleted or softened; a decision the user confirmed is never re-litigated; a replaced one is marked `superseded` and the new one added. *Facts* come from tool output, files, or the user only; correct with `edit` or a dated correction line. *Traps*: things that look right and are wrong. *Topic* changes only when the topic does.
   - *At a glance* (optional band above Now): `- **Label:** value` items, set with the `glance` key (`null` removes one). A few short values a reader needs first. Presets by kind of session, used as a starting point, not a rule:
     - incident or remediation: Status, Severity, Exposure, Gate, Owner
     - review queue: Open, Awaiting review, Blocked, Oldest
     - program or goals: Goal, Next due, Progress
     - inventory or answer bank: Scope, Coverage, Docset
     - ops domain: Systems, Open incidents
     `Status` renders as a pill; add `As of` when the values come from a dated source. A session without a band is fine.
   - *Sequence* (optional, for gated step-by-step work such as a cutover): numbered steps, each led by `[done]`, `[now]`, `[gated: why]`, `[blocked: why]` or `[todo]`. Change a state with `mark` (`["Sequence", "words", "gated: waiting on USAP"]`); steps are never archived. Keep Up next for the tasks around the sequence.
   - Each item is one or two sentences. Detail belongs in a linked doc or an attachment: a `<name>.<part>.md` file beside the checkpoint (for example `migration.facts.md`) is committed with it and listed on the page.
   - Date qualifiers are fine and render under the date: `2026-10-05 (Sam): ...`, `2026-10-01 PM: ...`.
   - Use the Edit tool only for what `patch` can't express (restructuring a section, a multi-paragraph block). Never write a Python or sed script to edit a checkpoint.
   - Header labels (`**Session:**`, `**Topic:**`, `**Checkpoint:**`, `**Artifact:**`) must stay; the helper stamps the time.
   - No credentials, secrets, or data your organization does not allow on claude.ai. Customer and incident detail only as needed to resume; the page is published to claude.ai. Prose is one paragraph per line.
3. **Finish.** `patch ... --finish` already ran it. Without a patch (an Edit-only change), run `checkpoint.py finish <name> --out <scratchpad>/checkpoint-render`.
   It applies markers and caps (Facts 15 in view, Recent sessions 5 distinct days), stamps the time, updates the register row, renders, commits only this session's files and attachments, and pushes. It prints `PUBLISH=no` when nothing changed: then skip publishing and reply. If it prints `PUSH HELD`, other work is unpushed on the register's branch; your checkpoint is committed locally and goes out with the next push. Tell the user in one line which commits are waiting; do not push them. If it prints `PUSH FAILED`, tell the user.
   `WARN=` lines report oversize items and sections, and Traps or Decisions past 25. They never block. Tighten only what you wrote this checkpoint; for older bulk, or a Traps/Decisions review, name it in one line in your reply and leave it to the user.
4. **Publish** the `HTML=` path with the Artifact tool, only if `PUBLISH=yes`.
   - `URL=` is set: pass it as `url`. Omit `icon`.
   - First publish: pass `icon` "pin" and a one-line description, then run `checkpoint.py set-url <name> <url> --out <scratchpad>/checkpoint-render` and publish its `HTML=` once more with that `url`.
   - If the Artifact tool is unavailable (API-key or cloud-provider session such as Bedrock or Vertex), say so and stop after finish.
   - Never hand-edit or restyle the HTML. Design changes go in `_template/checkpoint.css` or `shell.html`.
5. **Reply** with exactly three lines: state, last session, next step. Then stop.

## Game checkpoints

A header reading `**Kind:** game/<system>` means a game checkpoint: a campaign's adventure log, not a work queue. Before step 2, read `<register>/_template/kinds/game/SKILL.md` and use its section rules instead of the work ones. `new` picks the kind from the nearest `.claude/checkpoint.json` (for example `~/my-games/.claude/checkpoint.json`), or from `--kind game --system <id>`.

## Topic changes and segues

- `segue:` prompts never touch the checkpoint. Answer, then reprint the three lines.
- Rename onto an unregistered name: the prompt hook tells you once. Ask the user: segue or new topic? New topic: `--new`, and add a handoff line to the old checkpoint's References.
- Rename onto a registered name: ask the user: rejoin or new name? Rejoin: read that checkpoint first; the markers and append-only rules mean nothing is clobbered.
- Previous session under this name ended without a checkpoint (SessionStart NOTICE): say so in your opening lines; treat Now and Up next as possibly behind.
- Topic drift the user has not marked: ask once.
