---
name: bookmark-organizer
description: >-
  Organize, categorize, deduplicate, and clean up browser bookmarks using
  Chrome's native Bookmarks API via AppleScript. Use when the user asks to
  organize bookmarks, clean up bookmarks, sort bookmarks, find duplicate
  bookmarks, check for broken bookmark links, or manage their browser
  bookmark collection. Supports Chinese and English.
---

# Bookmark Organizer

Organize Chrome bookmarks through the browser's native API — no file hacking, no sync conflicts.

## Prerequisites Check

Before starting, verify:

1. **macOS only** — this skill uses AppleScript
2. **Chrome running** with at least one tab open
3. **"Allow JavaScript from Apple Events" enabled** in Chrome:
   - Menu → View → Developer → Allow JavaScript from Apple Events

If not enabled, guide the user to enable it before proceeding.

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

This is a conversational skill. The user drives the final structure:

1. **Start with top-level (L1) proposal only.** Don't overwhelm with deep nesting upfront.
2. **Ask if user wants sub-categories** for large folders (50+ items). If yes, propose L2.
3. **Support iterative deepening.** User may request further breakdown → propose L3 within that folder.
4. **Respect user overrides.** If user wants to move items to a different parent, adjust the plan.
5. **No fixed depth limit.** Support 2-level, 3-level, or even 4-level nesting if the user wants it.
6. **Confirm at each level** before creating folders and moving items.
7. **Use the user's language** for folder names. If user speaks Chinese, name folders in Chinese.

Example interaction flow:
```
Agent: "Proposed top-level structure: [L1 plan]. Shall I proceed, or adjust?"
User:  "Tech has too many items, break it down further"
Agent: "Got it. Proposed sub-categories for Tech: [L2 plan]. OK?"
User:  "Can you split Java Basics further?"
Agent: "Sure. Proposed sub-categories for Java Basics: [L3 plan]. OK?"
User:  "Looks good, go ahead"
Agent: → Execute all confirmed levels
```

### Phase 3: Execute Reorganization

Create folders and move bookmarks. Execute in batches to avoid overwhelming Chrome.

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

### Find Duplicate Bookmarks

```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.getTree(function(tree) {
  var urls = {};
  var dupes = [];
  function walk(node) {
    if (node.url) {
      var u = node.url.replace(/\\/$/,\"\");
      if (urls[u]) {
        dupes.push(node.id + \"|\" + urls[u] + \"|\" + u);
      } else {
        urls[u] = node.id;
      }
    }
    if (node.children) node.children.forEach(walk);
  }
  tree[0].children.forEach(walk);
  document.title = \"dupes:\" + dupes.length + \"|\" + dupes.slice(0,50).join(\";\");
});
\"scanning...\";
"'
```

Present duplicates to user and ask which to remove before deleting.

### Backup Current Structure

Before major changes, save the current tree as JSON to a local file:

```bash
osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "
chrome.bookmarks.getTree(function(tree) {
  document.title = JSON.stringify(tree).substring(0, 30000);
});
\"ok\";
"'
```

For large trees, save to a temp file in chunks. The backup serves as documentation; actual rollback uses `chrome.bookmarks.move()` to restore items to their original parent IDs.

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
- Keep JavaScript in AppleScript calls simple — complex scripts may hit shell escaping issues
