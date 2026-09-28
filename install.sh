#!/bin/bash
# Installs the /checkpoint skill, its hooks and a starter register. Never overwrites existing files
# except the skill and hooks themselves (backed up first). Does NOT edit settings.json or CLAUDE.md.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
REG="${CHECKPOINT_REGISTER:-$HOME/claude-session-register}"
STAMP=$(date +%Y%m%d%H%M%S)
backup() { [ -e "$1" ] && [ ! -L "$1" ] && cp "$1" "$1.bak-$STAMP" && echo "backed up $1"; return 0; }

mkdir -p "$HOME/.claude/skills/checkpoint" "$HOME/.claude/hooks/state"
backup "$HOME/.claude/skills/checkpoint/SKILL.md"
cp "$SRC/skill/SKILL.md" "$HOME/.claude/skills/checkpoint/SKILL.md"
for f in "$SRC"/hooks/*; do backup "$HOME/.claude/hooks/$(basename "$f")"; cp "$f" "$HOME/.claude/hooks/"; done
chmod +x "$HOME"/.claude/hooks/session-checkpoint-*.sh

mkdir -p "$REG/_template"
[ -e "$REG/README.md" ] || cp "$SRC/register/README.md" "$REG/README.md"
for f in "$SRC"/register/_template/*; do
  dst="$REG/_template/$(basename "$f")"; backup "$dst"; cp "$f" "$dst"
done
chmod +x "$REG/_template/"*.py
ln -sfn "$REG/_template/checkpoint.py" "$HOME/.claude/skills/checkpoint/checkpoint.py"
ln -sfn "$REG/_template/render.py" "$HOME/.claude/skills/checkpoint/render.py"

echo
echo "Installed. Register: $REG"
command -v pandoc >/dev/null || echo "MISSING: pandoc (brew install pandoc) - render.py needs it"
git -C "$REG" rev-parse --git-dir >/dev/null 2>&1 || echo "TODO: make $REG a git repo with a private remote: git -C \"$REG\" init && git -C \"$REG\" remote add origin <url> && commit + git push -u origin main"
echo "TODO: merge config/settings-snippet.json into ~/.claude/settings.json (hooks + allow rules)."
[ "$REG" = "$HOME/claude-session-register" ] || echo "      Your register is not the default: change the Edit/Write allow paths, and export CHECKPOINT_REGISTER=\"$REG\" in your shell profile."
echo "TODO: append config/CLAUDE-snippet.md to ~/.claude/CLAUDE.md."
