# Checkpoint template

Everything that shapes a session checkpoint, versioned together.

| File | Role |
|---|---|
| `SKILL.md` | The `/checkpoint` skill itself; `~/.claude/skills/checkpoint/SKILL.md` is a symlink here. |
| `TEMPLATE.md` | Section structure. `checkpoint.py new` copies it to `<session-name>.md`. Headings and bold labels are load-bearing for the renderer and helper. |
| `checkpoint.py` | Bookkeeping: `new`, `patch`, `finish`, `set-url`. `patch` applies one JSON edit all-or-nothing (the skill's normal write path). `finish` applies markers and caps, moves items to `<session-name>.archive.md`, removes blank lines inside lists, stamps the time, updates the register row, renders, commits only that session's files and attachments, pushes, and prints `WARN=` lines for oversize content. |
| `render.py` | Turns the checkpoint and its archive into the HTML page. |
| `checkpoint.css`, `shell.html` | The page design. Plain CSS and HTML with `{{PLACEHOLDER}}` slots; edit these to change the look. |
| `kinds/` | Alternative checkpoint kinds (for example `game`, with per-system themes). `new --kind`, or a project's `.claude/checkpoint.json`, selects one. See `kinds/README.md`. The default work kind is unaffected. |

**Markers** at the start of a list item: `[done]` (Up next, Waiting on), `[superseded]` (Decisions), `[obsolete]` (Traps), `[resolved]` (Unverified) move the item to the archive; `[pinned]` keeps a fact in view.

**Caps:** Facts in view 15, Recent sessions 5 distinct days (several entries on one day count once). Decisions and Traps are never archived by age, only by marker; the page folds all but the newest 12 under "Show N older".

**Archive:** `<session-name>.archive.md`, append only, rendered collapsed at the bottom of the same page. Each view section shows a breadcrumb such as "↓ 3 older facts in archive" that opens its archive group.

Design changes reach each session's page at its next checkpoint. Nothing republishes on its own.

**Test without touching the real register:** copy `_template/` and `README.md` into a scratch folder and run `checkpoint.py ... --no-git` from the copy; the helper works on the register folder that contains its own `_template/`.

**Attachments:** `<session-name>.<part>.md` beside the checkpoint (for example `migration.facts.md`) is committed with the checkpoint and listed on its page. Use one for detail too long for an item.

**Dates:** dated items may carry a short qualifier, `2026-10-05 (Sam):` or `2026-10-01 PM:` or `2026-10-08/09:`. Up to 18 characters shows under the date; a longer one leads the text.

**Size report:** `finish` warns on items over 500 characters, Now over 1,200, Up next over 6,000 bytes, a file over 30,000 bytes, and Traps or Decisions over 25. It never moves or cuts anything.

**At a glance / Sheet band:** an optional `## At a glance` (work) or `## Sheet` (game) section of `- **Label:** value` items renders as a band between the header and Now. Set it with `patch`'s `glance` key. Game sheets take their field order from `kinds/game/systems/<system>.json`.

**Sequence:** an optional `## Sequence` of numbered steps led by `[done]`, `[now]`, `[gated: why]`, `[blocked: why]` or `[todo]`, for gated step-by-step work. Steps are never archived.

**Sections per kind:** `render.py` lays out only its own kind's sections. Any other section renders as a plain block, so a work section named like a game one (Threads, Party) still shows.

