# Bookmark Organizer

An AI Agent Skill that intelligently organizes browser bookmarks — analyzing, categorizing, deduplicating, and restructuring your bookmark collection through natural language conversation.

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Smart Analysis** | ✅ | Analyze bookmark titles, URLs, and domains to recommend categories |
| **Interactive Planning** | ✅ | Show proposed structure before making changes, user confirms |
| **Create & Move** | ✅ | Create folders and move bookmarks using Chrome Bookmarks API |
| **Deduplicate** | 🚧 | Detect and merge duplicate URLs |
| **Dead Link Check** | 🚧 | Identify broken/404 links |
| **Backup & Rollback** | ✅ | Snapshot before changes, one-command restore |
| **Multi-browser** | 🔜 | Chrome (macOS) first; Safari, Firefox, Edge planned |

## How It Works

```
┌──────────────────────────────────────────────────────┐
│  User: "Help me organize my bookmarks"               │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  1. READ: Fetch bookmark tree via chrome.bookmarks   │
│     API through AppleScript (macOS)                  │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  2. ANALYZE: Count items, detect domains, suggest    │
│     categories based on URL patterns & titles        │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  3. PLAN: Present proposed folder structure to user  │
│     with item counts — user confirms or adjusts      │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  4. EXECUTE: Create folders, move bookmarks, clean   │
│     up empty folders — all via browser-native API    │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  5. VERIFY: Show final structure with counts         │
└──────────────────────────────────────────────────────┘
```

## Prerequisites

- **macOS** (uses AppleScript to communicate with Chrome)
- **Google Chrome** with "Allow JavaScript from Apple Events" enabled
  - Chrome menu → View → Developer → Allow JavaScript from Apple Events
- Chrome must be running with a tab open (any page works)

## Installation

### Cursor

```bash
# Copy to user-level skills (available in all projects)
cp -r bookmark-organizer ~/.cursor/skills/

# Or copy to a specific project
cp -r bookmark-organizer /path/to/project/.cursor/skills/
```

### Claude Code

```bash
cp -r bookmark-organizer ~/.claude/skills/
```

### OpenClaw

```bash
# Via ClawHub (when published)
openclaw skills install bookmark-organizer

# Or manual
cp -r bookmark-organizer ~/.agents/skills/
```

## Usage

Just ask your AI agent:

- "Help me organize my Chrome bookmarks"
- "整理一下我的 Chrome 书签"
- "Categorize my bookmarks into work, tech, and personal"
- "Find and remove duplicate bookmarks"
- "Check for broken bookmark links"

The agent will load this skill automatically based on the description triggers.

## Project Structure

```
bookmark-organizer/
├── SKILL.md                 # Main skill instructions (Cursor/Claude/OpenClaw)
├── README.md                # This file
├── scripts/
│   ├── chrome_bookmarks.sh  # AppleScript wrapper for Chrome Bookmarks API
│   ├── analyze.py           # Bookmark analysis and categorization
│   └── validate.py          # Post-operation validation
└── examples.md              # Example conversations and outputs
```

## How Chrome Bookmark Manipulation Works

Direct file modification of Chrome's `Bookmarks` JSON is unreliable because Chrome's cloud sync will revert changes. This skill uses **AppleScript → Chrome JavaScript execution** to call `chrome.bookmarks.*` API methods, which Chrome treats as internal operations and syncs correctly.

Key API calls used:
- `chrome.bookmarks.getTree()` — read full tree
- `chrome.bookmarks.create({parentId, title})` — create folder
- `chrome.bookmarks.move(id, {parentId})` — move item
- `chrome.bookmarks.remove(id)` / `removeTree(id)` — delete
- `chrome.bookmarks.search({url})` — find duplicates

## Contributing

PRs welcome! Areas where help is needed:
- Windows/Linux support (different browser automation approaches)
- Safari, Firefox, Edge support
- Smarter ML-based categorization
- Bookmark health checks (link validation)

## License

MIT
