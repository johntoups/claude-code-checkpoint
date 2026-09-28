#!/bin/bash
# SessionStart hook: tell the session its own name, its checkpoint, its artifact,
# and whether the previous session under this name ended without a checkpoint. Fails soft.
. "$HOME/.claude/hooks/session-checkpoint-lib.sh"
parse_input
TITLE=$(current_title "$TRANSCRIPT")

echo "[session-register] source=$SOURCE session_id=$SID"
echo "[session-register] transcript=$TRANSCRIPT"

if [ -z "$TITLE" ]; then
  echo "[session-register] This session has no custom title yet, so it is not registered."
  echo "[session-register] Rule: after the first substantive exchange, if the topic is clear propose a name, /rename, then /checkpoint --new <name>. Until then, do not create checkpoint files."
  exit 0
fi

echo "[session-register] Session name: $TITLE"
if ! title_is_safe "$TITLE"; then
  echo "[session-register] WARNING: this title is not filename-safe (slash, colon, backslash or leading dot). Ask the user to /rename before any checkpoint is written."
fi

MARK="$STATE_DIR/unchecked-$(safe_name "$TITLE")"
if [ -e "$MARK" ]; then
  echo "[session-register] NOTICE: the previous session named '$TITLE' ended $(cat "$MARK" 2>/dev/null) without a checkpoint after its last activity. The checkpoint file may be behind the transcript. Say so in your opening lines."
  rm -f "$MARK" 2>/dev/null || true
fi

ROW=$(register_row "$TITLE")
if [ -z "$ROW" ]; then
  echo "[session-register] '$TITLE' is not in the register ($REGISTER)."
  echo "[session-register] Rule: after the first substantive exchange, run /checkpoint --new $TITLE to create its checkpoint and artifact. If this session was renamed from a registered topic, ask the user: segue or new topic? Do not fork a checkpoint on your own judgment."
  exit 0
fi

CKPT=$(row_field "$ROW" 4); ART=$(row_field "$ROW" 5); LAST=$(row_field "$ROW" 6)
echo "[session-register] Checkpoint: $REGISTER_DIR/$CKPT (last checkpoint: $LAST)"
echo "[session-register] Artifact: $ART"
echo "[session-register] REQUIRED NOW: read the checkpoint file above, then open your first reply with a three-line 'where we are' (state, last session, next step) before anything else. The user should never have to ask where we are. Rules: ~/.claude/CLAUDE.md, 'Session Checkpoints'."
exit 0
