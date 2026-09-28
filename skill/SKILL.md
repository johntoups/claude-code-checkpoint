---
name: checkpoint
description: Write this session's checkpoint (now, next step, waiting on, up next, recent sessions, topic, decisions, facts, traps), then run checkpoint.py to archive, render, commit and push, and publish the designed HTML artifact. Use on wrap-up phrases, on /checkpoint, and with --new <name> to register a session for the first time.
---

You are the CHECKPOINT skill. One file per named session lets a resumed session, and the user, pick the work back up without asking "where are we". You write content. `checkpoint.py` does all bookkeeping. Keep token use low: edit sections in place, never rewrite the whole file.

## Locations

- Register: `$CHECKPOINT_REGISTER`, default `~/claude-session-register/` (README.md is the index; a private git repo, or a folder inside one)
- Checkpoint: `<register>/<session-name>.md`; archive: `<session-name>.archive.md` (written by the helper, read only when a question needs it)
- Template, design and helper: `<register>/_template/` (`TEMPLATE.md`, `checkpoint.css`, `shell.html`, `render.py`, `checkpoint.py`)
- Helper: `python3 ~/.claude/skills/checkpoint/checkpoint.py` (symlink)
- Render output: `<scratchpad>/checkpoint-render/` (your session's scratchpad directory)

## Session name

Use the name from the SessionStart hook's `[session-register] Session name:` line, or `grep '"type":"custom-title"' <transcript_path> | tail -1`. No name: ask the user. Never invent one. The helper refuses unsafe names and case-insensitive duplicates.

## Arguments

- `/checkpoint` — update this session's checkpoint.
- `/checkpoint --new <session-name>` — register it: `checkpoint.py new <name> "<one-line topic>"`, then fill the sections, then finish as below.

## Steps

0. **Live twin check.** List peer sessions. If another running session has this name, tell the user before writing; two live sessions on one checkpoint interleave. Proceed only if they say so.
1. **Read the checkpoint once** (not the archive). If it still has the old headings (Where we are, Last touched, Open items, Decisions made, Facts established, Pointers), migrate it now onto `_template/TEMPLATE.md`: carry every decision, fact, unverified item and trap across verbatim, split Open items into Waiting on, Up next and Parked, write Topic, start Recent sessions. Migration is the one case where a full rewrite is right.
2. **Edit only what changed, with the Edit tool, section by section.**
   - *Now*: rewrite the two or three state sentences and the `**Next step:**` line. Exactly one concrete action; it becomes the page's most prominent line.
   - *Waiting on*: bullets starting `**<user first name>:**`, `**External:**` or a named person. Everything needing the user goes here.
   - *Up next*: numbered, priority order, one sentence each. Add new items in position. Finished items: prefix `[done] `, do not delete; the helper archives them dated. `### Parked` holds deferred items with one clause of why.
   - *Recent sessions*: add or extend today's line at the top, `YYYY-MM-DD: what it did`. The helper keeps five and archives the rest.
   - *Topic*: `**Purpose:**`, `**Scope:**`, `**Out of scope:**`. Edit only when the topic itself changes.
   - *Decisions*: append `- YYYY-MM-DD: decision, and why.` Never delete or soften one; a decision the user confirmed is never re-litigated. Replaced decision: prefix it `[superseded] ` and append the new one.
   - *Facts*: append `- fact (source: ...)`. Tool output, files, or the user only. Correct with a dated correction line. Prefix `[pinned] ` to keep a fact in view past the 15-fact cap.
   - *Unverified*: `- Belief. Check: what confirms it.` Settled: prefix `[resolved] ` and add the result to Facts.
   - *Traps*: append. No longer true: prefix `[obsolete] `.
   - *References*: append.
   - Header labels (`**Session:**`, `**Topic:**`, `**Checkpoint:**`, `**Artifact:**`) must stay; the helper stamps the time.
   - No credentials, secrets, or data your organization does not allow on claude.ai. Customer and incident detail only as needed to resume; the page is published to claude.ai. Prose is one paragraph per line.
3. **Finish.** One command:
   ```bash
   python3 ~/.claude/skills/checkpoint/checkpoint.py finish <name> --out <scratchpad>/checkpoint-render
   ```
   It applies markers and caps, stamps the time, updates the register row, renders, commits only this session's files, and pushes. It prints `PUBLISH=no` when nothing changed: then skip publishing and reply. If it prints `PUSH HELD`, other work is unpushed on the register branch; your checkpoint is committed locally and goes out with the next push. Tell the user in one line which commits are waiting; do not push them. If it prints `PUSH FAILED`, tell the user.
4. **Publish** the `HTML=` path with the Artifact tool, only if `PUBLISH=yes`.
   - `URL=` is set: pass it as `url`. Omit icon.
   - First publish: pass icon `pin` and a one-line description, then run `checkpoint.py set-url <name> <url> --out <scratchpad>/checkpoint-render` and publish its `HTML=` once more with that `url`.
   - If the Artifact tool is unavailable (API-key or cloud-provider session), say so and stop after finish.
   - Never hand-edit or restyle the HTML. Design changes go in `_template/checkpoint.css` or `shell.html`.
5. **Reply** with exactly three lines: state, last session, next step. Then stop.

## Topic changes and segues

- `segue:` prompts never touch the checkpoint. Answer, then reprint the three lines.
- Rename onto an unregistered name: the prompt hook tells you once. Ask the user: segue or new topic? New topic: `--new`, and add a handoff line to the old checkpoint's References.
- Rename onto a registered name: ask the user: rejoin or new name? Rejoin: read that checkpoint first; the markers and append-only rules mean nothing is clobbered.
- Previous session under this name ended without a checkpoint (SessionStart NOTICE): say so in your opening lines; treat Now and Up next as possibly behind.
- Topic drift the user has not marked: ask once.
