#!/usr/bin/env python3
"""Chrome Bookmarks API wrapper via AppleScript on macOS.

Provides a Python interface to chrome.bookmarks.* API calls,
executed through AppleScript → Chrome JavaScript injection.

Usage:
    from chrome_api import ChromeBookmarks
    cb = ChromeBookmarks()
    tree = cb.get_tree()
    cb.create_folder(parent_id="1", title="New Folder")
    cb.move(bookmark_id="42", parent_id="100")
"""

import json
import subprocess
import time
import sys
from dataclasses import dataclass, field
from typing import Optional


WAIT_SECONDS = 2


@dataclass
class BookmarkNode:
    id: str
    title: str
    url: Optional[str] = None
    parent_id: Optional[str] = None
    children: list["BookmarkNode"] = field(default_factory=list)

    @property
    def is_folder(self) -> bool:
        return self.url is None

    def walk(self):
        """Yield all descendant nodes (depth-first)."""
        yield self
        for child in self.children:
            yield from child.walk()

    def walk_urls(self):
        """Yield only URL nodes."""
        for node in self.walk():
            if node.url:
                yield node

    def count_urls(self) -> int:
        return sum(1 for _ in self.walk_urls())


class ChromeError(Exception):
    pass


class ChromeBookmarks:
    def __init__(self, wait: float = WAIT_SECONDS):
        self.wait = wait

    def _run_js(self, js_code: str) -> str:
        """Execute JavaScript in Chrome's active tab and return document.title."""
        escaped = js_code.replace("\\", "\\\\").replace('"', '\\"')
        cmd = (
            f'tell application "Google Chrome" to execute front window\'s '
            f'active tab javascript "{escaped}"'
        )
        try:
            subprocess.run(
                ["osascript", "-e", cmd],
                capture_output=True, text=True, check=True, timeout=10,
            )
        except subprocess.CalledProcessError as e:
            raise ChromeError(f"AppleScript failed: {e.stderr.strip()}") from e
        except subprocess.TimeoutExpired:
            raise ChromeError("AppleScript timed out")

        time.sleep(self.wait)
        return self._read_title()

    def _read_title(self) -> str:
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "Google Chrome" to execute front window\'s '
                'active tab javascript "document.title"',
            ],
            capture_output=True, text=True, check=True, timeout=10,
        )
        return result.stdout.strip()

    @staticmethod
    def check_chrome_running():
        result = subprocess.run(
            ["pgrep", "-x", "Google Chrome"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ChromeError("Google Chrome is not running")

    # ── Read Operations ──

    def get_tree(self) -> list[BookmarkNode]:
        """Get the full bookmark tree as a flat list of top-level nodes."""
        self.check_chrome_running()

        self._run_js("""
chrome.bookmarks.getTree(function(tree) {
  var items = [];
  function walk(node, parentId) {
    var item = {id: node.id, title: node.title, parentId: parentId};
    if (node.url) item.url = node.url;
    if (node.children) {
      item.childIds = node.children.map(function(c) { return c.id; });
    }
    items.push(item);
    if (node.children) node.children.forEach(function(c) { walk(c, node.id); });
  }
  tree.forEach(function(root) { walk(root, null); });
  window._bkTree = items;
  window._bkChunkIdx = 0;
  document.title = 'tree-ready:' + items.length;
});
'reading...';
""")

        title = self._read_title()
        if not title.startswith("tree-ready:"):
            raise ChromeError(f"Unexpected response: {title}")

        total = int(title.split(":")[1])
        all_items = self._read_chunks(total)
        return self._build_tree(all_items)

    def _read_chunks(self, total: int, chunk_size: int = 150) -> list[dict]:
        """Read large data sets from Chrome in chunks."""
        all_items = []
        offset = 0

        while offset < total:
            self._run_js(f"""
var chunk = window._bkTree.slice({offset}, {offset + chunk_size});
document.title = JSON.stringify(chunk);
'ok';
""")
            raw = self._read_title()
            try:
                chunk = json.loads(raw)
                all_items.extend(chunk)
            except json.JSONDecodeError:
                raise ChromeError(f"Failed to parse chunk at offset {offset}")
            offset += chunk_size

        return all_items

    @staticmethod
    def _build_tree(items: list[dict]) -> list[BookmarkNode]:
        """Convert flat item list to a tree structure."""
        nodes: dict[str, BookmarkNode] = {}

        for item in items:
            node = BookmarkNode(
                id=item["id"],
                title=item.get("title", ""),
                url=item.get("url"),
                parent_id=item.get("parentId"),
            )
            nodes[node.id] = node

        roots = []
        for node in nodes.values():
            if node.parent_id and node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    def get_children(self, folder_id: str) -> list[dict]:
        """Get immediate children of a folder."""
        self.check_chrome_running()
        self._run_js(f"""
chrome.bookmarks.getChildren('{folder_id}', function(children) {{
  var items = children.map(function(c) {{
    return {{id: c.id, title: c.title, url: c.url || null}};
  }});
  document.title = JSON.stringify(items);
}});
'ok';
""")
        raw = self._read_title()
        return json.loads(raw)

    # ── Write Operations ──

    def create_folder(self, parent_id: str, title: str) -> str:
        """Create a folder and return its ID."""
        self.check_chrome_running()
        safe_title = title.replace("'", "\\'")
        self._run_js(f"""
chrome.bookmarks.create({{parentId: '{parent_id}', title: '{safe_title}'}}, function(f) {{
  document.title = 'created:' + f.id;
}});
'ok';
""")
        result = self._read_title()
        if not result.startswith("created:"):
            raise ChromeError(f"Failed to create folder: {result}")
        return result.split(":")[1]

    def move(self, bookmark_id: str, parent_id: str) -> bool:
        """Move a bookmark to a new parent folder."""
        self.check_chrome_running()
        self._run_js(f"""
chrome.bookmarks.move('{bookmark_id}', {{parentId: '{parent_id}'}}, function() {{
  document.title = 'moved:{bookmark_id}';
}});
'ok';
""")
        result = self._read_title()
        return result == f"moved:{bookmark_id}"

    def move_batch(self, bookmark_ids: list[str], parent_id: str) -> int:
        """Move multiple bookmarks to a parent folder. Returns count moved."""
        self.check_chrome_running()
        ids_js = ",".join(f"'{bid}'" for bid in bookmark_ids)
        self._run_js(f"""
var ids = [{ids_js}];
var target = '{parent_id}';
var done = 0;
ids.forEach(function(id) {{
  chrome.bookmarks.move(id, {{parentId: target}}, function() {{
    done++;
    if (done === ids.length) document.title = 'moved:' + done;
  }});
}});
'moving...';
""")
        result = self._read_title()
        if result.startswith("moved:"):
            return int(result.split(":")[1])
        return 0

    def remove(self, bookmark_id: str) -> bool:
        """Remove a bookmark or empty folder."""
        self.check_chrome_running()
        self._run_js(f"""
chrome.bookmarks.remove('{bookmark_id}', function() {{
  document.title = 'removed:{bookmark_id}';
}});
'ok';
""")
        result = self._read_title()
        return result == f"removed:{bookmark_id}"

    def remove_tree(self, folder_id: str) -> bool:
        """Remove a folder and all its contents."""
        self.check_chrome_running()
        self._run_js(f"""
chrome.bookmarks.removeTree('{folder_id}', function() {{
  document.title = 'removed:{folder_id}';
}});
'ok';
""")
        result = self._read_title()
        return result == f"removed:{folder_id}"

    # ── Analysis Operations ──

    def find_duplicates(self) -> list[dict]:
        """Find bookmarks with duplicate URLs. Returns list of duplicate groups."""
        tree = self.get_tree()
        url_map: dict[str, list[BookmarkNode]] = {}

        for root in tree:
            for node in root.walk_urls():
                normalized = node.url.rstrip("/")
                # Normalize http vs https for comparison
                if normalized.startswith("http://"):
                    alt = "https://" + normalized[7:]
                elif normalized.startswith("https://"):
                    alt = "http://" + normalized[8:]
                else:
                    alt = None

                matched_key = None
                if normalized in url_map:
                    matched_key = normalized
                elif alt and alt in url_map:
                    matched_key = alt

                if matched_key:
                    url_map[matched_key].append(node)
                else:
                    url_map[normalized] = [node]

        duplicates = []
        for url, nodes in url_map.items():
            if len(nodes) > 1:
                duplicates.append({
                    "url": url,
                    "count": len(nodes),
                    "instances": [
                        {"id": n.id, "title": n.title, "parent_id": n.parent_id}
                        for n in nodes
                    ],
                })

        return sorted(duplicates, key=lambda d: -d["count"])

    def get_summary(self) -> dict:
        """Get a summary of the bookmark structure."""
        tree = self.get_tree()
        # Bookmark Bar is tree[0].children[0], Other is tree[0].children[1]
        if not tree or not tree[0].children:
            return {"error": "No bookmarks found"}

        bar = tree[0].children[0] if len(tree[0].children) > 0 else None
        other = tree[0].children[1] if len(tree[0].children) > 1 else None

        summary = {"bookmark_bar": [], "other": []}

        for root_name, root_node in [("bookmark_bar", bar), ("other", other)]:
            if not root_node:
                continue
            for child in root_node.children:
                entry = {
                    "id": child.id,
                    "title": child.title,
                    "count": child.count_urls(),
                }
                if child.is_folder:
                    entry["subfolders"] = [
                        {"id": sub.id, "title": sub.title, "count": sub.count_urls()}
                        for sub in child.children
                        if sub.is_folder
                    ]
                summary[root_name].append(entry)

        return summary


# ── CLI ──

def main():
    if len(sys.argv) < 2:
        print("Usage: python chrome_api.py <command> [args...]")
        print("")
        print("Commands:")
        print("  tree              Print bookmark tree summary")
        print("  children ID       List children of folder")
        print("  create PID TITLE  Create folder")
        print("  move ID PID       Move bookmark to folder")
        print("  move-batch PID ID1 ID2 ...  Move multiple bookmarks")
        print("  remove ID         Remove bookmark")
        print("  dupes             Find duplicate URLs")
        print("  summary           Show structure summary")
        sys.exit(0)

    cb = ChromeBookmarks()
    cmd = sys.argv[1]

    if cmd == "tree":
        tree = cb.get_tree()
        def print_tree(node, indent=0):
            prefix = "  " * indent
            if node.url:
                print(f"{prefix}[{node.id}] {node.title} | {node.url}")
            else:
                print(f"{prefix}[{node.id}] \U0001f4c1 {node.title} ({node.count_urls()})")
            for child in node.children:
                print_tree(child, indent + 1)
        for root in tree:
            print_tree(root)

    elif cmd == "children":
        children = cb.get_children(sys.argv[2])
        print(json.dumps(children, ensure_ascii=False, indent=2))

    elif cmd == "create":
        new_id = cb.create_folder(sys.argv[2], sys.argv[3])
        print(f"Created folder: {new_id}")

    elif cmd == "move":
        ok = cb.move(sys.argv[2], sys.argv[3])
        print(f"Move {'succeeded' if ok else 'failed'}")

    elif cmd == "move-batch":
        parent = sys.argv[2]
        ids = sys.argv[3:]
        count = cb.move_batch(ids, parent)
        print(f"Moved {count} items")

    elif cmd == "remove":
        ok = cb.remove(sys.argv[2])
        print(f"Remove {'succeeded' if ok else 'failed'}")

    elif cmd == "dupes":
        dupes = cb.find_duplicates()
        if not dupes:
            print("No duplicates found.")
        else:
            print(f"Found {len(dupes)} duplicate URLs:\n")
            for i, d in enumerate(dupes, 1):
                print(f"{i}. {d['url']} (appears {d['count']} times)")
                for inst in d["instances"]:
                    print(f"   - [{inst['id']}] {inst['title']}")
                print()

    elif cmd == "summary":
        s = cb.get_summary()
        print(json.dumps(s, ensure_ascii=False, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
