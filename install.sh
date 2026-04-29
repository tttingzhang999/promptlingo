#!/usr/bin/env bash
# promptlingo installer: seed runtime data files from templates and link skill into ~/.claude/skills.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$REPO_DIR/skills/promptlingo"
DATA_DIR="$SKILL_DIR/data"
TEMPLATE_DIR="$DATA_DIR/templates"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "==> promptlingo install"
echo "    repo:   $REPO_DIR"
echo "    target: $CLAUDE_SKILLS_DIR/promptlingo"

mkdir -p "$DATA_DIR/reports"

for f in vocab.json patterns.json; do
  src="$TEMPLATE_DIR/$f"
  dst="$DATA_DIR/$f"
  if [[ ! -f "$src" ]]; then
    echo "    [ERROR] missing template: $src" >&2
    exit 1
  fi
  if [[ -f "$dst" ]]; then
    echo "    [skip] $f already exists"
  else
    cp "$src" "$dst"
    echo "    [init] $f seeded from template"
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
