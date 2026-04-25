# Bookmark Organizer

**English** | [中文](README.zh-CN.md)

An AI Agent Skill that organizes your browser bookmarks through natural language conversation — analyze, categorize, deduplicate, and restructure your bookmark collection.

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Smart Analysis** | ✅ | Analyzes bookmark titles, URLs, and domains to recommend categorization |
| **Interactive Planning** | ✅ | Shows proposed structure for user approval before making changes |
| **Create & Move** | ✅ | Creates folders and moves bookmarks via Chrome Bookmarks API |
| **Deduplication** | ✅ | Detects and merges duplicate URLs (with http/https normalization) |
| **Backup & Restore** | ✅ | Auto-snapshots before changes; one-click rollback if unhappy |
| **Multi-browser** | ✅ | Chrome & Doubao Browser (macOS); Safari, Firefox, Edge planned |

## How It Works

```
┌─────────────────────────────────────────────────────┐
│  User: "Help me organize my bookmarks"              │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  1. Read: Fetch full bookmark tree via AppleScript  │
│     → chrome.bookmarks API                          │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  2. Analyze: Count items, cluster by domain,        │
│     suggest categories based on URL patterns        │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  3. Plan: Present proposed folder structure          │
│     with item counts; wait for user confirmation    │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  4. Execute: Create folders, move bookmarks,         │
│     clean up empty folders — all via native API     │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│  5. Verify: Show final structure and category counts │
└─────────────────────────────────────────────────────┘
```

## Supported Browsers

| Key | Browser | macOS App Name |
|-----|---------|---------------|
| `chrome` | Google Chrome (default) | Google Chrome |
| `doubao` | 豆包浏览器 (Doubao Browser) | Doubao Browser |

## Prerequisites

- **macOS** (uses AppleScript to communicate with the browser)
- **Google Chrome** or **Doubao Browser** with "Allow JavaScript from Apple Events" enabled
  - Browser menu → View → Developer → Allow JavaScript from Apple Events
- The browser must be running with at least one tab open

## Installation

### One-line Install (Recommended)

```bash
git clone https://github.com/kyruntime/bookmark-organizer.git
cd bookmark-organizer

# Install for Cursor
./install.sh --cursor

# Install for Claude Code
./install.sh --claude

# Install for all supported platforms
./install.sh --all
```

`install.sh` creates a symlink to `~/.cursor/skills/` (or the corresponding platform directory). Future code updates take effect automatically.

### Manual Install

```bash
# Cursor
cp -r bookmark-organizer ~/.cursor/skills/

# Claude Code
cp -r bookmark-organizer ~/.claude/skills/
```

## Usage

Just tell the AI Agent:

- "Help me organize my Chrome bookmarks"
- "Help me organize my Doubao Browser bookmarks"
- "Find duplicate bookmarks"
- "Split the Tech folder into sub-categories"

The agent automatically loads this skill based on trigger words in the skill description.

## Project Structure

```
bookmark-organizer/
├── SKILL.md                   # Skill definition (Cursor/Claude Code/OpenClaw)
├── README.md                  # This file
├── README.zh-CN.md            # Chinese documentation
├── install.sh                 # One-line installer
├── examples.md                # Usage examples
├── scripts/
│   ├── chrome_api.py          # Core Python library (unified API entry point)
│   ├── backup_restore.py      # Backup & one-click restore
│   ├── analyze.py             # Bookmark analysis & categorization suggestions
│   ├── validate.py            # Post-reorganization structure validation
│   └── smoke_test.py          # Smoke tests
└── .gitignore
```

## Backup & Restore

The agent **automatically creates a backup** before any reorganization. You can also manage backups manually:

```bash
# Create a backup (saved to ~/.bookmark-organizer/backups/)
python3 scripts/backup_restore.py backup

# List all backups
python3 scripts/backup_restore.py list

# Restore from a backup (interactive confirmation)
python3 scripts/backup_restore.py restore ~/.bookmark-organizer/backups/bookmarks_20260421_143000.json

# Skip confirmation (used by the agent)
python3 scripts/backup_restore.py restore <backup_file> --yes
```

Backup files record each bookmark's ID, title, URL, and parent folder. Restore uses `chrome.bookmarks.move()` to return each bookmark to its original location.

## Deduplication

```bash
# Scan for duplicate bookmarks
python3 scripts/chrome_api.py dupes
```

Supports URL normalization (ignores trailing slashes, http/https differences). Duplicates are shown to the user for confirmation before deletion.

## Verify Installation

Run the smoke test to confirm everything works (requires Chrome running):

```bash
cd bookmark-organizer
python3 scripts/smoke_test.py
```

Expected output: `Results: 6/6 passed`.

> **Note**: The script automatically opens a new Chrome tab at `chrome://bookmarks` (the API only works on that page) and closes it when done. A temporary test folder is created and immediately deleted — your bookmarks are not affected.

## Multi-browser Support

All commands and Python APIs support the `-b`/`--browser` parameter:

```bash
# Default: Google Chrome
python3 scripts/chrome_api.py tree

# Doubao Browser (豆包浏览器)
python3 scripts/chrome_api.py -b doubao tree
python3 scripts/backup_restore.py -b doubao backup
python3 scripts/smoke_test.py -b doubao
```

Or via the Python API:
```python
from chrome_api import ChromeBookmarks
cb = ChromeBookmarks(browser="doubao")
```

## How It Works (Technical)

Directly modifying the browser's `Bookmarks` JSON file is unreliable — cloud sync will revert the changes.

This skill uses **AppleScript → Browser JavaScript execution** to call `chrome.bookmarks.*` APIs. The browser treats these as internal operations and syncs them correctly.

Core API calls:
- `chrome.bookmarks.getTree()` — Read the full bookmark tree
- `chrome.bookmarks.create({parentId, title})` — Create a folder
- `chrome.bookmarks.move(id, {parentId})` — Move a bookmark
- `chrome.bookmarks.remove(id)` / `removeTree(id)` — Delete
- `chrome.bookmarks.search({url})` — Search / dedup

## Contributing

PRs welcome! Areas that need help:
- Windows / Linux support (requires alternative browser automation)
- More Chromium-based browsers (Arc, Brave, Edge, etc.)
- Safari, Firefox support
- Smarter ML-based categorization

## License

MIT
