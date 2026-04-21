#!/usr/bin/env bash
# Install bookmark-organizer skill for Cursor, Claude Code, and/or OpenClaw.
# Usage: ./install.sh [--cursor] [--claude] [--openclaw] [--all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="bookmark-organizer"

install_cursor() {
  local target="$HOME/.cursor/skills/$SKILL_NAME"
  mkdir -p "$(dirname "$target")"
  if [ -L "$target" ] || [ -d "$target" ]; then
    rm -rf "$target"
  fi
  ln -s "$SCRIPT_DIR" "$target"
  echo "Cursor: installed → $target"
}

install_claude() {
  local target="$HOME/.claude/skills/$SKILL_NAME"
  mkdir -p "$(dirname "$target")"
  if [ -L "$target" ] || [ -d "$target" ]; then
    rm -rf "$target"
  fi
  ln -s "$SCRIPT_DIR" "$target"
  echo "Claude Code: installed → $target"
}

install_openclaw() {
  local target="$HOME/.agents/skills/$SKILL_NAME"
  mkdir -p "$(dirname "$target")"
  if [ -L "$target" ] || [ -d "$target" ]; then
    rm -rf "$target"
  fi
  ln -s "$SCRIPT_DIR" "$target"
  echo "OpenClaw: installed → $target"
}

if [ $# -eq 0 ]; then
  echo "Usage: $0 [--cursor] [--claude] [--openclaw] [--all]"
  echo ""
  echo "Creates symlinks from AI tool skill directories to this folder."
  echo "Supports multiple flags at once."
  exit 0
fi

for arg in "$@"; do
  case "$arg" in
    --cursor)   install_cursor ;;
    --claude)   install_claude ;;
    --openclaw) install_openclaw ;;
    --all)
      install_cursor
      install_claude
      install_openclaw
      ;;
    *)
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

echo ""
echo "Done! The skill will be available next time the AI agent loads."
