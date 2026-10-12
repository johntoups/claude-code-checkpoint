# /checkpoint — session checkpoints for Claude Code

Every named Claude Code session keeps one Markdown checkpoint (state, next step, waiting on, up next, decisions, facts, traps). On start, resume, `/clear` or compaction, a hook tells Claude where that checkpoint is, and Claude opens its first reply with three lines: state, last session, next step. You never have to ask "where were we". Each checkpoint is also rendered to a designed HTML page and published as a private claude.ai artifact.

## Install with Claude Code

Paste this into Claude Code:

```
Clone https://github.com/johntoups/claude-code-checkpoint to ~/src/claude-code-checkpoint,
read FOR-CLAUDE.md and every file it names, then install /checkpoint for me following it.
Ask me before changing settings.json or CLAUDE.md.
```

`FOR-CLAUDE.md` tells your Claude that this package is a generalized copy of someone else's working setup. It also says what to keep as-is, what to ask you, and how to verify the install without touching a real register.

## What's in here

| Path | Installs to | Role |
|---|---|---|
| `skill/SKILL.md` | `<register>/_template/SKILL.md`, symlinked from `~/.claude/skills/checkpoint/` | The `/checkpoint` skill: what Claude writes and in what order |
| `hooks/session-checkpoint-start.sh` | `~/.claude/hooks/` | SessionStart: prints session name, checkpoint path, artifact URL; tells Claude to open with the three lines |
| `hooks/session-checkpoint-prompt.sh` | `~/.claude/hooks/` | UserPromptSubmit: wrap-up phrases trigger a checkpoint; `segue:` prefix; rename detection |
| `hooks/session-checkpoint-end.sh` | `~/.claude/hooks/` | SessionEnd: marks a session that ended with un-checkpointed work, reported at next start |
| `hooks/session-checkpoint-lib.sh` | `~/.claude/hooks/` | Shared helpers |
| `hooks/checkpoint-wrapup-phrases.txt` | `~/.claude/hooks/` | Phrases ("wrap up", "done for today"…) that trigger a checkpoint. Edit freely |
| `register/README.md` | `~/claude-session-register/` | The register: one table row per session. Hooks read it |
| `register/_template/` | `~/claude-session-register/_template/` | `TEMPLATE.md` (sections), `checkpoint.py` (new / patch / finish / set-url: one-call structured edits, archive, caps, size warnings, commit, push), `render.py` + `checkpoint.css` + `shell.html` (the page) |
| `register/_template/kinds/` | `~/claude-session-register/_template/kinds/` | Alternative checkpoint kinds. `game`: adventure log, character-sheet band, per-system sheet fields (`systems/`) and themes (Dragonbane, Traveller), and its own skill rules. A project's `.claude/checkpoint.json` selects it |
| `config/settings-snippet.json` | merge into `~/.claude/settings.json` | Hook registrations and allow rules |
| `config/CLAUDE-snippet.md` | append to `~/.claude/CLAUDE.md` | The rules Claude follows |

## Paths and what they're for

In the original setup these paths were hardcoded to one person's machine. Each one was replaced with the setting below. Change one and you may need to change the others listed with it.

| Path / setting | Default | Purpose | Who reads it | If you change it |
|---|---|---|---|---|
| **Register folder** (`$CHECKPOINT_REGISTER`) | `~/claude-session-register/` | The permanent record. Holds `README.md` (the index table), one `<session>.md` per session, its `<session>.archive.md`, and `_template/`. It has to be in git, because git history is the only full version history (the artifact keeps just recent versions). | All three hooks through `session-checkpoint-lib.sh`; `checkpoint.py` locates it as the parent of its own `_template/` folder | Export `CHECKPOINT_REGISTER` in your shell profile so the hooks see it, and update the `Edit`/`Write` allow paths in settings |
| **Register git remote** | none; you supply it | Backup and history for checkpoints. **Must be private.** Checkpoints hold internal decisions and ticket details. | `checkpoint.py finish` pushes to the branch's upstream | Any private repo works. The register can be the repo root or a subfolder of a larger private docs repo |
| **Push guard scope** | the register's path within its repo | Makes `finish` push only when every unpushed commit touches files inside the register. Otherwise it prints `PUSH HELD`, so a checkpoint never pushes unrelated work. | `checkpoint.py` (`git rev-parse --show-prefix`) | Nothing to set. If the register is the repo root, every commit counts as a register commit |
| `register/README.md` table | inside the register | Maps session name to checkpoint file, artifact URL and last-checkpoint date. Hooks look up the session by its `/rename` title in the first column. | hooks (read), `checkpoint.py` (read/write) | Keep the five-column pipe table format. The parsers depend on it |
| `~/.claude/skills/checkpoint/` | fixed | Where Claude Code finds the skill. `checkpoint.py` and `render.py` here are **symlinks** into the register's `_template/`, so the design and helper are versioned with the register | Claude Code; the skill calls `python3 ~/.claude/skills/checkpoint/checkpoint.py` | Don't move it. Claude Code discovers skills only here (or in a project's `.claude/skills/`) |
| `~/.claude/hooks/` | fixed by these scripts | Hook scripts, the shared lib and the wrap-up phrase list | `settings.json` hook commands; the scripts source the lib from `$HOME/.claude/hooks/` | If you move them, update the `settings.json` commands and the `. "$HOME/.claude/hooks/..."` source lines and `PHRASES=` in the scripts |
| `~/.claude/hooks/state/` | fixed | Scratch markers. SessionEnd writes `unchecked-<session>` when a session ended more than 10 minutes after its last checkpoint. The next SessionStart reports the marker and deletes it. | end and start hooks | Safe to delete at any time. Not version-controlled |
| `<scratchpad>/checkpoint-render/` | the session's scratchpad dir | Where `finish` writes the rendered HTML before the Artifact tool publishes it. This output is disposable; the Markdown is the record. | the skill passes it as `--out` | Any temp folder. Never commit it |
| Artifact URL | set on first publish | The claude.ai page for this session. `set-url` writes it back into the checkpoint header and the register row, because the gallery can't be relied on to find old pages | start hook prints it; the skill republishes to it | Don't hand-edit it. A new URL means a new page |
| `$CHECKPOINT_OWNER` | first word of `git config user.name` | The label on your items in `Waiting on`. The page highlights `**needs <name>**` as a chip | `checkpoint.py new` | Set it if your git name isn't what you want on the page |

## What a checkpoint does

- **Writing:** the skill puts one JSON change list through `checkpoint.py patch` (all or nothing), which also runs `finish`. That keeps a checkpoint to a few tool calls instead of many hand edits.
- **Bookkeeping:** `finish` archives marked items, caps Facts (15 in view) and Recent sessions (5 distinct days), commits only that session's files and its attachments (`<session>.<part>.md`), pushes, and prints `WARN=` lines for oversize items. It never cuts content.
- **The page:** a dark Now band with the single next step, an optional **At a glance** band above it (work) or **character sheet** (game), a section bar with counts, an optional **Sequence** of gated steps, dated ledgers that accept short qualifiers (`2026-10-05 (Sam):`), and the archive folded at the bottom.
- **Kinds:** `work` is the default. `game` turns the page into an adventure log with a sheet band, "Where we left off", and a next-game date chip.

## Requirements

- Claude Code, `python3`, `git`, `pandoc` (`brew install pandoc`)
- A **private** git repo for the register (new repo, or a folder inside an existing private one)
- Publishing needs a claude.ai-authenticated session. API-key or cloud-provider (Bedrock, Vertex) sessions still write, commit and push the checkpoint; they just skip the artifact.

## Install

1. `./install.sh` — copies skill, hooks and template; symlinks `checkpoint.py` and `render.py` into the skill folder. Backs up anything it replaces. Does not touch `settings.json` or `CLAUDE.md`.
   - Different register location: `CHECKPOINT_REGISTER=~/path/to/register ./install.sh`, and export the same `CHECKPOINT_REGISTER` in your shell profile so the hooks find it.
2. Make the register a git repo with a private remote and push once with `-u` so the branch has an upstream:
   ```bash
   cd ~/claude-session-register && git init -b main && git remote add origin <private-repo-url>
   git add -A && git commit -m "register" && git push -u origin main
   ```
3. Merge `config/settings-snippet.json` into `~/.claude/settings.json` (add to existing `hooks` arrays; don't replace them). If your register isn't the default path, change the two `Edit`/`Write` allow paths.
4. Append `config/CLAUDE-snippet.md` to `~/.claude/CLAUDE.md`.
5. Restart Claude Code.

## Use

- In a session: `/rename my-topic`, then `/checkpoint --new my-topic`. Claude fills the sections and publishes the page.
- Afterwards: `/checkpoint`, or say a wrap-up phrase. Resume the session later (or `/clear`) and Claude reads the checkpoint and gives you the three lines first.
- `segue: <question>` answers without touching the checkpoint.
- Mark items rather than deleting them: `[done]`, `[superseded]`, `[obsolete]`, `[resolved]` move to `<name>.archive.md` (shown collapsed on the page); `[pinned]` keeps a fact in view. See `register/_template/README.md`.
- The `Waiting on` owner label comes from `$CHECKPOINT_OWNER`, else the first word of `git config user.name`.

## Notes

- **Keep sensitive data out of checkpoints.** The page is published to claude.ai: no credentials, secrets, or data your organization does not allow there.
- `checkpoint.py finish` commits only the session's own files. If the register lives inside a bigger repo and other unpushed commits are waiting, it commits locally and prints `PUSH HELD` rather than pushing someone else's work.
- Same session name = same checkpoint. Two live sessions with the same name will interleave writes; the skill checks for this first.
- Change the page design in `_template/checkpoint.css` / `shell.html`; it reaches each page at its next checkpoint.
