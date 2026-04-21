---
name: bookmark-organizer
description: >-
  Organize, categorize, deduplicate, and clean up browser bookmarks using
  Chrome's native Bookmarks API via AppleScript. Use when the user asks to
  organize bookmarks, clean up bookmarks, sort bookmarks, find duplicate
  bookmarks, or manage their browser bookmark collection.
---

# Bookmark Organizer

Organize Chrome bookmarks through the browser's native API — no file hacking, no sync conflicts.

## Prerequisites Check

Before starting, run through these checks:

1. **Ask which browser** if the user didn't specify. Currently only **Google Chrome on macOS** is supported.
   - If the user mentions Safari, Firefox, or Edge, explain that support is coming soon and this skill currently only works with Chrome.
2. **macOS only** — this skill uses AppleScript to communicate with Chrome.
3. **Chrome must be running** with at least one tab open.
4. **"Allow JavaScript from Apple Events" must be enabled** in Chrome:
   - Menu → View → Developer → Allow JavaScript from Apple Events
   - If the user gets an authorization error, guide them to this setting.

The skill will automatically open a new Chrome tab for `chrome://bookmarks/` (the API only works on that page) and close it when done. The user's existing tabs are not affected.

**Do NOT activate or bring Chrome to the foreground.** Use `set URL of active tab` only, not `activate`. The user should stay in their current application (Cursor) while the skill operates on Chrome in the background.

## Core Workflow

### Phase 1: Read Bookmark Tree

**Always use the Python API** — it handles tab management, async polling, and chunked reads automatically:

```bash
# Print the full bookmark tree
python3 {baseDir}/scripts/chrome_api.py tree

# Or get a summary with folder counts
python3 {baseDir}/scripts/chrome_api.py summary

# List children of a specific folder
python3 {baseDir}/scripts/chrome_api.py children FOLDER_ID
```

The Python API automatically opens a new Chrome tab for `chrome://bookmarks/` and closes it when done. The user's existing tabs are never affected.

### Phase 2: Analyze and Plan

After reading the tree, analyze it and propose a reorganization plan.

**Analysis checklist:**
- Total bookmark count and folder count
- Identify domain clusters (e.g., many github.com links → "Dev Tools")
- Detect uncategorized bookmarks (items directly in bookmark bar)
- Find obvious groupings by title keywords
- Identify existing folder structures worth preserving

**Default category suggestions** (adapt based on actual content; name folders in whatever language the user is using — do NOT mention the language choice to the user, just use it naturally):

| Pattern | Typical Content |
|---------|----------------|
| Work-{CompanyName} | Company-specific tools, dashboards, internal systems |
| Tech / Learning | Programming tutorials, docs, Stack Overflow, GitHub repos |
| AI & Tools | AI tools, ChatGPT, Cursor, productivity apps |
| Daily Tools | Email, calendar, cloud storage, utilities |
| Life / Personal | Shopping, entertainment, health, finance |
| Archive | Old/rarely used bookmarks worth keeping |

**Present the plan to the user before executing.** Use a tree format with item counts:

```
Proposed structure:
├── Work-Acme (45 links)
│   ├── Dashboard (20)
│   └── Internal Docs (25)
├── Tech (120 links)
│   ├── Java (30)
│   ├── Frontend (25)
│   └── ...
├── AI & Tools (15 links)
└── Personal (40 links)
```

**Wait for user confirmation before proceeding.**

#### Interactive Planning Rules

This is a conversational skill. The user drives the final structure.

**First, assess the current state:**
- If bookmarks are **well-organized** (most items in named folders with clear hierarchy), show the **complete existing structure** (all levels) and ask "What would you like to adjust?"
- If bookmarks are **messy** (many uncategorized items, flat structure, no clear folders), propose a reorganization plan starting from L1.

**Planning rules:**

1. **Show the full existing structure** when reading bookmarks — always include all levels (L1, L2, L3+), not just top-level. The user needs to see the complete picture to make decisions.
2. **Propose changes based on what needs fixing**, not a full rewrite. If the structure is already 80% good, only suggest the 20% that needs work.
3. **Share your own observations and suggestions.** Don't just show the data — tell the user what you think could be improved and why. For example: "This folder has 200+ items, splitting by topic would make it easier to find things", or "These 3 folders overlap in content, merging them would reduce clutter". Be opinionated but open to the user's preferences.
4. **Ask the user for their own ideas.** After presenting your analysis and suggestions, ask: "Do you have any specific ideas or preferences for how you'd like to organize these?" The user may have their own mental model or workflow that the data alone can't reveal.
5. **Ask if user wants sub-categories** for large folders (50+ items). If yes, propose sub-folders.
6. **Support iterative deepening.** User may request further breakdown → propose deeper nesting within that folder.
7. **Respect user overrides.** If user wants to move items to a different parent, adjust the plan.
8. **No fixed depth limit.** Support 2-level, 3-level, or even 4-level nesting if the user wants it.
9. **Show a before/after preview** before executing. Present the proposed final structure (what it will look like after the changes) alongside what it looks like now, so the user can visualize the result.
10. **Confirm before executing** any changes.
11. **Match the user's language** — respond and name folders in whatever language the user is using. Do not assume any specific language.

Example interaction for **already organized** bookmarks:
```
Agent: "Your bookmarks are already well-organized:
  ├── Work-Acme (50)
  │   ├── Dashboard (20)
  │   └── Docs (30)
  ├── Tech (120)
  │   ├── Java (30) ...
  └── Personal (40)
  What would you like to adjust?"
User:  "Tech is too crowded, split it more"
Agent: "Here's Tech currently: [full L2+L3 listing]. I suggest..."
```

Example interaction for **messy** bookmarks:
```
Agent: "You have 500 bookmarks, most are uncategorized. Here's my proposed structure:
  [full multi-level plan]. Shall I proceed?"
User:  "Looks good, go ahead"
Agent: → Execute
```

### Phase 3: Execute Reorganization

**Before making any changes, create a backup:**
```bash
python3 {baseDir}/scripts/backup_restore.py backup
```
After the backup completes, **tell the user the backup file path** so they know where to find it if they need to restore later.

Then create folders and move bookmarks using the Python API:

**Create a folder:**
```bash
python3 {baseDir}/scripts/chrome_api.py create PARENT_ID "Folder Name"
```

**Move a bookmark to a folder:**
```bash
python3 {baseDir}/scripts/chrome_api.py move BOOKMARK_ID TARGET_FOLDER_ID
```

**Move multiple bookmarks at once:**
```bash
python3 {baseDir}/scripts/chrome_api.py move-batch TARGET_FOLDER_ID ID1 ID2 ID3
```

**Delete an empty folder:**
```bash
python3 {baseDir}/scripts/chrome_api.py remove FOLDER_ID
```

For complex sequences (many creates + moves), use Python directly for better control:
```python
import sys; sys.path.insert(0, "{baseDir}/scripts")
from chrome_api import ChromeBookmarks
cb = ChromeBookmarks()
folder_id = cb.create_folder("1", "New Category")
cb.move_batch(["42", "43", "44"], folder_id)
cb.cleanup()
```

### Phase 4: Verify

After all operations, read the final tree and present it to the user:

```bash
python3 {baseDir}/scripts/chrome_api.py summary
```

Or for a full tree view:
```bash
python3 {baseDir}/scripts/chrome_api.py tree
```

## Advanced Operations

### Find and Remove Duplicate Bookmarks

Use the Python API for dedup — it normalizes URLs (trailing slash, http/https) for more accurate matching:

```bash
python3 {baseDir}/scripts/chrome_api.py dupes
```

This prints all duplicate groups with their IDs and locations. Present the results to the user in a clear table format, then ask which copies to remove. For each removal, use:

```bash
python3 {baseDir}/scripts/chrome_api.py remove BOOKMARK_ID
```

**Dedup rules:**
- Never auto-delete without user confirmation
- When asking which to keep, suggest keeping the copy in the more specific/relevant folder
- After removal, verify no orphaned folders remain

### Backup & Restore

**Always create a backup before any reorganization.** Run the backup script:

```bash
python3 {baseDir}/scripts/backup_restore.py backup
```

This saves every bookmark's ID, title, URL, and parentId to `~/.bookmark-organizer/backups/bookmarks_YYYYMMDD_HHMMSS.json`. The agent should run this automatically at the start of Phase 3 (before any moves).

**List available backups:**
```bash
python3 {baseDir}/scripts/backup_restore.py list
```

**Restore from a backup** (moves all bookmarks back to their original parent folders):
```bash
python3 {baseDir}/scripts/backup_restore.py restore <backup_file> --yes
```
Use `--yes` to skip the interactive confirmation prompt (required when called by an agent).

The restore works by calling `chrome.bookmarks.move()` for each item to return it to its original parent — same sync-safe API, no file hacking.

If the user says they're unhappy with the result or wants to undo, immediately offer to restore from the most recent backup.

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `execution error: Not authorized` | JS from Apple Events not enabled | Guide user to Chrome → View → Developer → Allow JavaScript from Apple Events |
| `Can't get window 1` | No Chrome window open | Ask user to open Chrome with any tab |
| Bookmark IDs not found | Chrome restarted (IDs change) | Re-read the tree to get fresh IDs |
| `document.title` empty | Async callback not completed | Increase sleep time between execute and read |

## Important Notes

- **Never modify the Bookmarks JSON file directly** — Chrome sync will revert changes
- All operations go through `chrome.bookmarks.*` API → sync-safe
- Bookmark IDs are session-stable but may change across Chrome restarts
- **Check both Bookmark Bar AND "Other Bookmarks"** — users may have items in both locations
- **Always use `scripts/chrome_api.py`** — do NOT write raw AppleScript/osascript commands. The Python API handles tab management, escaping, async polling, and chunked reads automatically
- Always call `cb.cleanup()` after using `ChromeBookmarks` directly in Python to close the helper tab
