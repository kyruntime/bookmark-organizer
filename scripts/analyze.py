#!/usr/bin/env python3
"""Analyze Chrome bookmarks and suggest categories.

Usage:
    python analyze.py              # Read from Chrome via API (default)
    python analyze.py --json FILE  # Read from a local bookmarks JSON file

Output: JSON report with stats, domain clusters, and suggested categories.
"""

import json
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

from chrome_api import ChromeBookmarks, BookmarkNode

DOMAIN_CATEGORIES = {
    "github.com": "Dev Tools",
    "gitlab.com": "Dev Tools",
    "stackoverflow.com": "Tech Learning",
    "developer.mozilla.org": "Tech Learning",
    "docs.oracle.com": "Tech Learning",
    "spring.io": "Tech Learning",
    "baeldung.com": "Tech Learning",
    "juejin.cn": "Tech Learning",
    "csdn.net": "Tech Learning",
    "cnblogs.com": "Tech Learning",
    "zhihu.com": "Daily Tools",
    "bilibili.com": "Media",
    "youtube.com": "Media",
    "notion.so": "Daily Tools",
    "figma.com": "Design",
    "chat.openai.com": "AI",
    "claude.ai": "AI",
    "cursor.com": "AI",
    "docs.google.com": "Daily Tools",
    "drive.google.com": "Daily Tools",
    "mail.google.com": "Daily Tools",
    "taobao.com": "Life",
    "jd.com": "Life",
    "amazon.com": "Life",
}


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        parts = host.split(".")
        if len(parts) > 2 and parts[-2] not in ("com", "co", "org", "net"):
            return ".".join(parts[-2:])
        elif len(parts) > 2:
            return ".".join(parts[-3:])
        return host
    except Exception:
        return ""


def analyze_tree(roots: list[BookmarkNode]) -> dict:
    all_bookmarks: list[dict] = []
    all_folders: list[dict] = []

    for root in roots:
        for node in root.walk():
            if node.url:
                depth = _node_depth(node, roots)
                all_bookmarks.append({
                    "id": node.id,
                    "title": node.title,
                    "url": node.url,
                    "parent_id": node.parent_id,
                    "depth": depth,
                })
            elif node.is_folder:
                depth = _node_depth(node, roots)
                all_folders.append({
                    "id": node.id,
                    "name": node.title,
                    "depth": depth,
                    "bookmark_count": node.count_urls(),
                })

    domains = Counter()
    domain_to_bookmarks: dict[str, list[dict]] = defaultdict(list)
    uncategorized = []

    for bm in all_bookmarks:
        domain = extract_domain(bm["url"])
        domains[domain] += 1
        domain_to_bookmarks[domain].append(bm)
        if bm["depth"] <= 1:
            uncategorized.append(bm)

    suggested: dict[str, list[dict]] = defaultdict(list)
    for domain, bms in domain_to_bookmarks.items():
        category = None
        for known_domain, cat in DOMAIN_CATEGORIES.items():
            if domain.endswith(known_domain):
                category = cat
                break
        if category:
            suggested[category].extend(bms)

    url_counts = Counter(bm["url"].rstrip("/") for bm in all_bookmarks)
    duplicates = [
        {"url": url, "count": count}
        for url, count in url_counts.items()
        if count > 1
    ]

    return {
        "stats": {
            "total_bookmarks": len(all_bookmarks),
            "total_folders": len(all_folders),
            "uncategorized_in_root": len(uncategorized),
            "duplicate_urls": len(duplicates),
        },
        "top_domains": domains.most_common(20),
        "suggested_categories": {
            cat: {
                "count": len(bms),
                "sample_titles": [b["title"] for b in bms[:5]],
            }
            for cat, bms in sorted(suggested.items(), key=lambda x: -len(x[1]))
        },
        "duplicates": duplicates[:20],
        "folder_structure": [
            {"name": f["name"], "depth": f["depth"], "count": f["bookmark_count"]}
            for f in all_folders
            if f["depth"] <= 2
        ],
    }


def _node_depth(node: BookmarkNode, roots: list[BookmarkNode]) -> int:
    """Calculate depth by counting ancestor levels. Simple BFS approach."""
    id_to_parent: dict[str, str | None] = {}
    for root in roots:
        for n in root.walk():
            id_to_parent[n.id] = n.parent_id

    depth = 0
    current = node.parent_id
    while current and current in id_to_parent:
        depth += 1
        current = id_to_parent[current]
    return depth


def main():
    use_file = None
    if len(sys.argv) >= 3 and sys.argv[1] == "--json":
        use_file = sys.argv[2]

    if use_file:
        from pathlib import Path
        data = json.loads(Path(use_file).read_text(encoding="utf-8"))
        roots_data = data.get("roots", {})
        bar = roots_data.get("bookmark_bar", {})
        other = roots_data.get("other", {})
        all_bookmarks_raw = []

        def walk_raw(node, depth=0):
            if node.get("type") == "url":
                all_bookmarks_raw.append({
                    "id": node.get("id"),
                    "title": node.get("name", ""),
                    "url": node.get("url", ""),
                    "depth": depth,
                })
            for child in node.get("children", []):
                walk_raw(child, depth + 1)

        walk_raw(bar)
        walk_raw(other)

        domains = Counter()
        for bm in all_bookmarks_raw:
            domain = extract_domain(bm["url"])
            domains[domain] += 1

        report = {
            "stats": {"total_bookmarks": len(all_bookmarks_raw)},
            "top_domains": domains.most_common(20),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        cb = ChromeBookmarks()
        tree = cb.get_tree()
        report = analyze_tree(tree)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
