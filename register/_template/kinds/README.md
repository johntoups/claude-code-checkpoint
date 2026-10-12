# Checkpoint kinds

A kind is an alternative checkpoint structure and layout for a class of session. The default kind, **work**, is `../TEMPLATE.md` with the base design, and it is unchanged by anything here.

| Path | Role |
|---|---|
| `<kind>/TEMPLATE.md` | Section structure for the kind. `checkpoint.py new` copies it, filling `{{SYSTEM}}`. |
| `<kind>/<kind>.css` | Layout layer for the kind, built only from the base tokens. Appended after `checkpoint.css`. |
| `<kind>/SKILL.md` | The kind's section rules for the `/checkpoint` skill, read only when a checkpoint's header names this kind. |
| `<kind>/systems/<system>.json` | Game kind: the Sheet band's identity, stat and track fields for a system, in display order. |
| `<kind>/themes/<system>.css` | Optional per-system theme: token overrides for light and dark, plus the label face. Appended last. |

A theme or layer may start with `/* @fonts <url> */`. The renderer adds that stylesheet in the page head. Work pages get no extra head, and render byte-identical to before kinds existed.

## Choosing a kind

`checkpoint.py new <name> "<topic>" --kind game --system dragonbane`, or let the project choose. With no `--kind`, `new` walks up from the working directory to the nearest `.claude/checkpoint.json`:

```json
{ "kind": "game",
  "sessions": { "my-campaign": { "system": "dragonbane", "campaign": "campaigns/my_campaign" } } }
```

The kind and system are then written into the checkpoint header as `**Kind:** game/dragonbane`. `render.py` reads them from there, so the register table is untouched. A game session with no system errors instead of guessing.

## game

Sections: Sheet (the character-sheet band, shown above Now), Now (rendered as "Where we left off", with **Next game:** above **Next step:**; the first date in Next game becomes a date chip), Between games, **Adventure log**, Character, Party, Threads, NPCs, Table rulings, Facts, Unverified, Traps, References.

- **Adventure log**: one `### Session N · YYYY-MM-DD · Title` per game session, oldest first in the file. Session 0 is character creation. Each entry is a few lines plus a link to the campaign's full session file; the campaign folder stays the source of truth. The log is **never capped or archived**. The page shows the newest session open and the older ones folded.
- **Between games**: bullets led by `**<your name>:**` or `**GM:**`. `[done]` archives them to Done.
- **Threads**: `[resolved]` archives them to Resolved threads.
- **Table rulings**: dated and append-only, like Decisions. `[superseded]` archives them.
- **Traps** means *in-fiction* traps the party has met, such as a pressure plate, a poisoned needle, or a statue that swings a sword. It does not mean the work kind's "things that look right and are wrong". Rules and table gotchas go in Facts. The heading is the same so the helper and renderer need no change, and only the meaning differs.
- No Recent sessions section. The Adventure log replaces it.

Themes present: `dragonbane` (parchment, woodcut serif, moss and ochre), `traveller` (the little black books: black band, signal red, condensed technical type). Add a system by writing `themes/<system>.css` against the base tokens. Without one, a game page still renders, in the base colours.

Systems with sheet fields: `dragonbane` (Name, Kin, Profession, Age · STR CON AGL INT WIL CHA · HP WP Move), `traveller` (Name, Career, Homeworld, Age · STR DEX END INT EDU SOC · Luck, Credits, Ship).
