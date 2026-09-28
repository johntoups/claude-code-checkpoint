# Shared helpers for the session-checkpoint hooks. Sourced, not executed.
REGISTER_DIR="${CHECKPOINT_REGISTER:-$HOME/claude-session-register}"
REGISTER="$REGISTER_DIR/README.md"
STATE_DIR="$HOME/.claude/hooks/state"

# Parse hook stdin JSON into shell vars: TRANSCRIPT SOURCE SID PROMPT SCRATCH REASON
parse_input() {
  eval "$(python3 -c '
import json,sys,shlex
try: d=json.load(sys.stdin)
except Exception: d={}
for k,v in (("TRANSCRIPT","transcript_path"),("SOURCE","source"),("SID","session_id"),("PROMPT","prompt"),("SCRATCH","scratchpad_dir"),("REASON","reason")):
    print(k+"="+shlex.quote(str(d.get(v,"") or "")))
' 2>/dev/null)"
}

# Distinct custom titles in order of appearance, one per line.
titles_in_transcript() {
  [ -n "$1" ] && [ -r "$1" ] || return 0
  grep '"type":"custom-title"' "$1" 2>/dev/null | python3 -c 'import json,sys
out=[]
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    try: t=json.loads(l).get("customTitle","")
    except Exception: continue
    if t and (not out or out[-1]!=t): out.append(t)
print("\n".join(out))' 2>/dev/null
}

current_title() { titles_in_transcript "$1" | tail -1; }

# Register row for a title, case-insensitive on the first column. Prints the row or nothing.
register_row() {
  [ -r "$REGISTER" ] || return 0
  awk -F'|' -v want="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" '
    NF>=6 { n=$2; gsub(/^[ \t]+|[ \t]+$/,"",n); if (tolower(n)==want) { print; exit } }' "$REGISTER"
}
row_field() { printf '%s' "$1" | awk -F'|' -v i="$2" '{gsub(/^[ \t]+|[ \t]+$/,"",$i); print $i}'; }

safe_name() { printf '%s' "$1" | tr -c 'A-Za-z0-9_-' '_'; }

# A title is filename-safe if it has no slash, colon, backslash, or leading dot, and is non-empty.
title_is_safe() {
  case "$1" in ''|*/*|*:*|*\\*|.*) return 1;; esac
  return 0
}

# File mtime in epoch seconds; portable across macOS and Linux.
mtime() { python3 -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$1" 2>/dev/null || echo 0; }
