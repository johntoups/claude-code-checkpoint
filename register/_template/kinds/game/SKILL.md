# Checkpoint skill: game kind

Read this instead of the work section rules in `../../SKILL.md` step 2 when the checkpoint header reads `**Kind:** game/<system>`. Every other step (patch, finish, publish, reply) is the same.

## Game checkpoints

A header reading `**Kind:** game/<system>` means a game checkpoint. It is a campaign's adventure log, not a work queue. `new` picks the kind from the nearest `.claude/checkpoint.json` (for example `~/my-games/.claude/checkpoint.json`), or from `--kind game --system <id>`. Structure and rules: `_template/kinds/README.md`. In step 2, `patch` these sections instead of the work ones (`next_game` sets **Next game:**; `add` takes `Between games`, `Threads`, `NPCs`, `Table rulings`, and `Adventure log` as a raw Markdown block starting with its `###` heading; use `edit` to update a character, party or NPC line in place):

- *Now*: where the party is in the fiction, and what was hanging. Keep `**Next game:**` (when and where) above `**Next step:**` (the one thing to do before or at the start of it).
- *Between games*: `**<your name>:**` or `**GM:**` bullets. `[done]` when finished.
- *Adventure log*: append `### Session N · YYYY-MM-DD · Title` for each game played, oldest first. Session 0 is character creation. Write three to six lines of what happened, then link `sessions/session_YYYY-MM-DD.md`. The campaign folder is the source of truth; this is the index. Never delete or cap entries.
- *Character*, *Party*: update in place. The character sheet file and the VTT are authoritative.
- *Threads*: `[resolved]` when closed. *NPCs*: append, and update an attitude in place.
- *Traps* (game kind only): **in-fiction traps the party has met**, as `- **Where**: what sets it off, what it did; sprung / disarmed / still armed (S#).` Update the status in place. This is not the work meaning. Rules or table gotchas go in *Facts*.
- *Table rulings*: `- YYYY-MM-DD: ruling (GM).` Append only, like Decisions. A GM ruling is never re-litigated.
- There is no Recent sessions section. Claude-side work (tooling, fixes) goes in References only if it matters to the game.
- Spoilers: never write published-module content the players haven't met in play.
- *Sheet* (the character-sheet band above Where we left off): set values with `patch`'s `glance` key, for example `{"glance": {"HP": "7", "WP": "4", "As of": "Session 2"}}`; `null` removes a field. Field names and order come from `systems/<system>.json`; any other label shows as an extra cell. Update it after each game from the sheet file or Foundry, never from memory, and keep **As of** current.
- A new system: add `systems/<system>.json` (identity, stats, tracks) and optionally `themes/<system>.css`.
