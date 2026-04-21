#!/usr/bin/env python3
"""Analyze Chrome bookmarks and suggest categories.

Usage:
    python analyze.py <bookmarks_json_file>
    python analyze.py --from-chrome

When --from-chrome is used, reads the macOS default Chrome Bookmarks file.
Output: JSON report with stats, domain clusters, and suggested categories.
"""

import json
import sys
import os
from collections import Counter, defaultdict
from urllib.parse import urlparse
from pathlib import Path

CHROME_BOOKMARKS_PATH = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
)

DOMAIN_CATEGORIES = {
    "github.com": "开发工具",
    "gitlab.com": "开发工具",
    "stackoverflow.com": "技术学习",
    "developer.mozilla.org": "技术学习",
    "docs.oracle.com": "技术学习",
    "spring.io": "技术学习",
    "baeldung.com": "技术学习",
    "juejin.cn": "技术学习",
    "csdn.net": "技术学习",
    "cnblogs.com": "技术学习",
    "zhihu.com": "日常工具",
    "bilibili.com": "影音娱乐",
    "youtube.com": "影音娱乐",
    "notion.so": "日常工具",
    "figma.com": "设计",
    "chat.openai.com": "AI",
    "claude.ai": "AI",
    "cursor.com": "AI",
    "docs.google.com": "日常工具",
    "drive.google.com": "日常工具",
    "mail.google.com": "日常工具",
    "taobao.com": "生活",
    "jd.com": "生活",
    "amazon.com": "生活",
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


def walk_bookmarks(node, path="", depth=0):
    """Yield (id, title, url, path, depth) for every bookmark."""
    current_path = f"{path}/{node.get('name', '')}" if path else node.get("name", "")

    if node.get("type") == "url":
        yield {
            "id": node.get("id"),
            "title": node.get("name", ""),
            "url": node.get("url", ""),
            "path": path,
            "depth": depth,
        }

    for child in node.get("children", []):
        yield from walk_bookmarks(child, current_path, depth + 1)


def walk_folders(node, depth=0):
    """Yield (id, name, depth, child_count) for every folder."""
    if node.get("type") == "folder":
        bookmark_count = sum(
            1 for _ in walk_bookmarks(node)
        )
        yield {
            "id": node.get("id"),
            "name": node.get("name", ""),
            "depth": depth,
            "bookmark_count": bookmark_count,
        }
        for child in node.get("children", []):
            yield from walk_folders(child, depth + 1)


def analyze(bookmarks_data: dict) -> dict:
    roots = bookmarks_data.get("roots", {})
    bar = roots.get("bookmark_bar", {})
    other = roots.get("other", {})

    all_bookmarks = list(walk_bookmarks(bar)) + list(walk_bookmarks(other))
    all_folders = list(walk_folders(bar)) + list(walk_folders(other))

    domains = Counter()
    domain_to_bookmarks = defaultdict(list)
    uncategorized = []

    for bm in all_bookmarks:
        domain = extract_domain(bm["url"])
        domains[domain] += 1
        domain_to_bookmarks[domain].append(bm)
        if bm["depth"] <= 1:
            uncategorized.append(bm)

    suggested = defaultdict(list)
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


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <bookmarks.json | --from-chrome>")
        sys.exit(1)

    source = sys.argv[1]
    if source == "--from-chrome":
        path = Path(CHROME_BOOKMARKS_PATH)
        if not path.exists():
            print(f"Chrome bookmarks not found at {CHROME_BOOKMARKS_PATH}")
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))

    report = analyze(data)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
