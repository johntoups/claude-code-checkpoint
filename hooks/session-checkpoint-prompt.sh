#!/bin/bash
# UserPromptSubmit hook: wrap-up phrases, segue prefix, rename onto an unregistered name,
# rename onto a registered name. Silent on ordinary prompts. Fails soft.
. "$HOME/.claude/hooks/session-checkpoint-lib.sh"
PHRASES=$HOME/.claude/hooks/checkpoint-wrapup-phrases.txt
parse_input
LOWER=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')

# 1. Segue.
case "$LOWER" in
  segue:*|segue\ *|"segue -"*)
    echo "[session-register] SEGUE. Answer this prompt without touching the checkpoint, the register, or any topic files. When done, reprint the three-line 'where we are' for the registered topic so the thread is re-anchored. If the segue grows past a quick answer, say so and ask whether it should become its own session."
    ;;
esac

# 2. Wrap-up phrases.
if [ -r "$PHRASES" ] && [ -n "$LOWER" ]; then
  while IFS= read -r p; do
    case "$p" in ''|\#*) continue;; esac
    pl=$(printf '%s' "$p" | tr '[:upper:]' '[:lower:]')
    case "$LOWER" in
      *"$pl"*)
        echo "[session-register] WRAP-UP detected ('$p'). Before replying: run the /checkpoint skill in full (update the checkpoint file, publish the artifact if the Artifact tool is available, write the URL back, commit and push the register). Then reply with the three-line 'where we are' and stop. If this session has no checkpoint yet, create it now with /checkpoint --new <session name>."
        break
        ;;
    esac
  done < "$PHRASES"
fi

# 3. Renames. Fire once per session per title, using a marker in the scratchpad.
TITLES=$(titles_in_transcript "$TRANSCRIPT")
N=$(printf '%s\n' "$TITLES" | grep -c .)
CUR=$(printf '%s\n' "$TITLES" | tail -1)
if [ "$N" -gt 1 ] && [ -n "$CUR" ]; then
  PREV=$(printf '%s\n' "$TITLES" | tail -2 | head -1)
  MARK=""
  [ -n "$SCRATCH" ] && [ -d "$SCRATCH" ] && MARK="$SCRATCH/.register-rename-asked-$(safe_name "$CUR")"
  if [ -z "$MARK" ] || [ ! -e "$MARK" ]; then
    ROW=$(register_row "$CUR")
    if [ -z "$ROW" ]; then
      echo "[session-register] Session was renamed from '$PREV' to '$CUR' and '$CUR' is not in the register. Ask the user once: is this a segue or a new topic? New topic: /checkpoint --new $CUR, and add a handoff line to the old checkpoint. Do not fork on your own."
    else
      LAST=$(row_field "$ROW" 6); CKPT=$(row_field "$ROW" 4)
      echo "[session-register] Session was renamed from '$PREV' onto '$CUR', which already has a checkpoint ($REGISTER_DIR/$CKPT, last written $LAST). Ask the user once: rejoin that topic, or pick a new name? Rejoin: read that checkpoint before the next /checkpoint, and reconcile rather than overwrite (decisions, facts and traps are append-only; open items are merged). New name: /rename, then /checkpoint --new."
    fi
    [ -n "$MARK" ] && touch "$MARK" 2>/dev/null || true
  fi
fi
exit 0
