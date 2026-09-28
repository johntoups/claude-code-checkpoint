# Checkpoint template

Everything that shapes a session checkpoint, versioned together.

| File | Role |
|---|---|
| `TEMPLATE.md` | Section structure. `checkpoint.py new` copies it to `<session-name>.md`. Headings and bold labels are load-bearing for the renderer and helper. |
| `checkpoint.py` | Bookkeeping: `new`, `finish`, `set-url`. Applies markers and caps, moves items to `<session-name>.archive.md`, stamps the time, updates the register row, renders, commits only that session's files, pushes. |
| `render.py` | Turns the checkpoint and its archive into the HTML page. |
| `checkpoint.css`, `shell.html` | The page design. Plain CSS and HTML with `{{PLACEHOLDER}}` slots; edit these to change the look. |

**Markers** at the start of a list item: `[done]` (Up next, Waiting on), `[superseded]` (Decisions), `[obsolete]` (Traps), `[resolved]` (Unverified) move the item to the archive; `[pinned]` keeps a fact in view.

**Caps:** Facts in view 15, Recent sessions 5. Decisions and Traps are never archived by age, only by marker; the page folds all but the newest 12 under "Show N older".

**Archive:** `<session-name>.archive.md`, append only, rendered collapsed at the bottom of the same page. Each view section shows a breadcrumb such as "↓ 3 older facts in archive" that opens its archive group.

Design changes reach each session's page at its next checkpoint. Nothing republishes on its own.

**Owner label:** `checkpoint.py new` fills the `Waiting on` owner label from `$CHECKPOINT_OWNER`, else the first word of `git config user.name`.

**Test without touching the real register:** copy `_template/` and `README.md` into a scratch folder and run `checkpoint.py ... --no-git` from the copy; the helper works on the register folder that contains its own `_template/`.
