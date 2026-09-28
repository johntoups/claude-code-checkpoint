#!/bin/bash
# SessionEnd hook: if the session had activity after its last checkpoint, leave a marker
# that the next SessionStart under this name reports. Cannot run the model; only records.
. "$HOME/.claude/hooks/session-checkpoint-lib.sh"
parse_input
TITLE=$(current_title "$TRANSCRIPT")
[ -n "$TITLE" ] || exit 0
ROW=$(register_row "$TITLE")
[ -n "$ROW" ] || exit 0            # unregistered sessions have nothing to be behind
CKPT="$REGISTER_DIR/$(row_field "$ROW" 4)"
[ -r "$CKPT" ] && [ -r "$TRANSCRIPT" ] || exit 0
T_CK=$(mtime "$CKPT")
T_TR=$(mtime "$TRANSCRIPT")
# More than 10 minutes of transcript activity after the checkpoint file was last written.
if [ $((T_TR - T_CK)) -gt 600 ]; then
  mkdir -p "$STATE_DIR"
  date '+%Y-%m-%d %H:%M' > "$STATE_DIR/unchecked-$(safe_name "$TITLE")"
fi
exit 0
