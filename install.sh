#!/usr/bin/env bash
# promptlingo installer: seed the learning folder and link the skill into ~/.claude/skills.
# Set PROMPTLINGO_LEARNING_DIR to write into an Obsidian vault; the default is <skill>/learning.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEARNING_DIR="${PROMPTLINGO_LEARNING_DIR:-$SKILL_DIR/learning}"
TEMPLATE_DIR="$SKILL_DIR/data/templates"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "==> promptlingo install"
echo "    skill:    $SKILL_DIR"
echo "    learning: $LEARNING_DIR"
echo "    target:   $CLAUDE_SKILLS_DIR/promptlingo"

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

mkdir -p "$CLAUDE_SKILLS_DIR"
link="$CLAUDE_SKILLS_DIR/promptlingo"
if [[ -L "$link" ]]; then
  current="$(readlink "$link")"
  if [[ "$current" == "$SKILL_DIR" ]]; then
    echo "    [skip] symlink already points to $SKILL_DIR"
  else
    echo "    [warn] symlink exists, points to $current (leaving as-is)"
  fi
elif [[ -e "$link" ]]; then
  echo "    [warn] $link exists and is not a symlink (leaving as-is)"
else
  ln -s "$SKILL_DIR" "$link"
  echo "    [link] $link -> $SKILL_DIR"
fi

echo "==> done"
