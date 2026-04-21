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

The skill will automatically navigate Chrome's active tab to `chrome://bookmarks/` (the API only works on `chrome://` pages).

**Do NOT activate or bring Chrome to the foreground.** Use `set URL of active tab` only, not `activate`. The user should stay in their current application (Cursor) while the skill operates on Chrome in the background.

## Core Workflow

### Phase 1: Read Bookmark Tree

```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.getTree(function(tree) {
  var bar = tree[0].children[0];
  var lines = [];
  function walk(node, depth) {
    var prefix = \"\";
    for(var i=0;i<depth;i++) prefix += \"  \";
    if (node.url) {
      lines.push(prefix + \"[\" + node.id + \"] \" + node.title + \" | \" + node.url);
    } else {
      var cnt = 0;
      function count(n) { if(n.url) cnt++; else if(n.children) n.children.forEach(count); }
      count(node);
      lines.push(prefix + \"[\" + node.id + \"] 📁 \" + node.title + \" (\" + cnt + \")\");
      if (node.children) node.children.forEach(function(c) { walk(c, depth+1); });
    }
  }
  bar.children.forEach(function(c) { walk(c, 0); });
  document.title = JSON.stringify(lines);
});
\"reading...\";
"'
```

Wait 2 seconds, then read result:
```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "document.title"'
```

**Important**: `document.title` has a practical limit of ~30KB. For large bookmark collections (500+ items), read in chunks by folder ID:

```bash
# Read children of a specific folder
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.getChildren(\"FOLDER_ID\", function(children) {
  var lines = children.map(function(c) {
    return c.url ? c.id+\"|\"+c.title+\"|\"+c.url : c.id+\"|📁\"+c.title;
  });
  document.title = JSON.stringify(lines);
});
\"ok\";
"'
```

### Phase 2: Analyze and Plan

After reading the tree, analyze it and propose a reorganization plan.

**Analysis checklist:**
- Total bookmark count and folder count
- Identify domain clusters (e.g., many github.com links → "Dev Tools")
- Detect uncategorized bookmarks (items directly in bookmark bar)
- Find obvious groupings by title keywords
- Identify existing folder structures worth preserving

**Default category suggestions** (adapt based on actual content; use the user's language for folder names):

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
3. **Ask if user wants sub-categories** for large folders (50+ items). If yes, propose sub-folders.
4. **Support iterative deepening.** User may request further breakdown → propose deeper nesting within that folder.
5. **Respect user overrides.** If user wants to move items to a different parent, adjust the plan.
6. **No fixed depth limit.** Support 2-level, 3-level, or even 4-level nesting if the user wants it.
7. **Show a before/after preview** before executing. Present the proposed final structure (what it will look like after the changes) alongside what it looks like now, so the user can visualize the result.
8. **Confirm before executing** any changes.
9. **Match the user's language** — respond and name folders in whatever language the user is using. Do not assume any specific language.

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
bash {baseDir}/scripts/backup_restore.sh backup
```

Then create folders and move bookmarks. Execute in batches to avoid overwhelming Chrome.

**Create a folder:**
```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.create({parentId: \"PARENT_ID\", title: \"FOLDER_NAME\"}, function(f) {
  document.title = \"created:\" + f.id;
});
\"ok\";
"'
```

**Move items (batch of up to 20):**
```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
var ids = [\"ID1\",\"ID2\",\"ID3\"];
var target = \"TARGET_FOLDER_ID\";
var done = 0;
ids.forEach(function(id) {
  chrome.bookmarks.move(id, {parentId: target}, function() {
    done++;
    if (done === ids.length) document.title = \"moved:\" + done;
  });
});
\"moving...\";
"'
```

**Delete empty folder:**
```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.removeTree(\"FOLDER_ID\", function() {
  document.title = \"deleted\";
});
\"ok\";
"'
```

**Batch rules:**
- Move at most 20 items per AppleScript call
- Wait 1-2 seconds between batches
- Always verify via `document.title` after each operation
- If an operation fails, log the error and continue with the next batch

### Phase 4: Verify

After all operations, read the final tree structure and present it to the user:

```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.getTree(function(tree) {
  var bar = tree[0].children[0];
  var lines = [];
  bar.children.forEach(function(c) {
    var cnt = 0;
    function count(n) { if(n.url) cnt++; else if(n.children) n.children.forEach(count); }
    count(c);
    lines.push(c.title + \": \" + cnt);
    if (c.children) {
      c.children.forEach(function(sub) {
        if (!sub.url) {
          var scnt = 0;
          function scount(n) { if(n.url) scnt++; else if(n.children) n.children.forEach(scount); }
          scount(sub);
          lines.push(\"  > \" + sub.title + \": \" + scnt);
        }
      });
    }
  });
  document.title = lines.join(\"|\");
});
\"ok\";
"'
```

## Advanced Operations

### Find and Remove Duplicate Bookmarks

Use the Python API for dedup — it normalizes URLs (trailing slash, http/https) for more accurate matching:

```bash
python3 {baseDir}/scripts/chrome_api.py dupes
```

This prints all duplicate groups with their IDs and locations. Present the results to the user in a clear table format, then ask which copies to remove. For each removal, use:

```bash
python3 -c "
from scripts.chrome_api import ChromeBookmarks
cb = ChromeBookmarks()
cb.remove('BOOKMARK_ID')
"
```

**Dedup rules:**
- Never auto-delete without user confirmation
- When asking which to keep, suggest keeping the copy in the more specific/relevant folder
- After removal, verify no orphaned folders remain

### Backup & Restore

**Always create a backup before any reorganization.** Run the backup script:

```bash
bash {baseDir}/scripts/backup_restore.sh backup
```

This saves every bookmark's ID, title, URL, and parentId to `~/.bookmark-organizer/backups/bookmarks_YYYYMMDD_HHMMSS.json`. The agent should run this automatically at the start of Phase 3 (before any moves).

**List available backups:**
```bash
bash {baseDir}/scripts/backup_restore.sh list
```

**Restore from a backup** (moves all bookmarks back to their original parent folders):
```bash
bash {baseDir}/scripts/backup_restore.sh restore <backup_file> --yes
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
- The "Bookmarks Bar" is always `tree[0].children[0]`, "Other Bookmarks" is `tree[0].children[1]`
- **Check both Bookmark Bar AND "Other Bookmarks"** — users may have items in both locations
- When folder names contain single quotes or backslashes, escape them before injecting into AppleScript JS calls (replace `'` with `\\'`)
- Keep JavaScript in AppleScript calls simple — complex scripts may hit shell escaping issues
- **Prefer the Python API** (`scripts/chrome_api.py`) over raw AppleScript for complex operations — it handles escaping, async polling, and chunked reads automatically
