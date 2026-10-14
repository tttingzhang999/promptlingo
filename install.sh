#!/usr/bin/env bash
# promptlingo installer: seed the learning folder and link the skill into ~/.claude/skills and ~/.codex/skills.
# Set PROMPTLINGO_LEARNING_DIR to write into an Obsidian vault; the default is <skill>/learning.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEARNING_DIR="${PROMPTLINGO_LEARNING_DIR:-$SKILL_DIR/learning}"
TEMPLATE_DIR="$SKILL_DIR/data/templates"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"

echo "==> promptlingo install"
echo "    skill:    $SKILL_DIR"
echo "    learning: $LEARNING_DIR"
echo "    targets:  $CLAUDE_SKILLS_DIR/promptlingo, $CODEX_SKILLS_DIR/promptlingo"

mkdir -p "$LEARNING_DIR/data" "$LEARNING_DIR/reports" "$LEARNING_DIR/glossary" "$LEARNING_DIR/grammar"

for f in vocab.json patterns.json; do
  src="$TEMPLATE_DIR/$f"
  dst="$LEARNING_DIR/data/$f"
  if [[ ! -f "$src" ]]; then
    echo "    [ERROR] missing template: $src" >&2
    exit 1
  fi
  if [[ -f "$dst" ]]; then
    echo "    [skip] $f already exists"
  else
    cp "$src" "$dst"
    echo "    [init] $f seeded"
  fi
done

link_skill() {
  local dir="$1" link="$1/promptlingo"
  mkdir -p "$dir"
  if [[ -L "$link" ]]; then
    local current
    current="$(readlink "$link")"
    if [[ "$current" == "$SKILL_DIR" ]]; then
      echo "    [skip] $link already points to $SKILL_DIR"
    else
      echo "    [warn] $link points to $current (leaving as-is)"
    fi
  elif [[ -e "$link" ]]; then
    echo "    [warn] $link exists and is not a symlink (leaving as-is)"
  else
    ln -s "$SKILL_DIR" "$link"
    echo "    [link] $link -> $SKILL_DIR"
  fi
}

[[ -d "$HOME/.claude" ]] && link_skill "$CLAUDE_SKILLS_DIR"
[[ -d "$HOME/.codex" ]] && link_skill "$CODEX_SKILLS_DIR"

echo "==> done"
