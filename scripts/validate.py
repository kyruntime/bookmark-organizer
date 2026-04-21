#!/usr/bin/env python3
"""Validate bookmark structure after reorganization.

Usage:
    python validate.py            # Read from Chrome via API (default)
    python validate.py --pipe TEXT # Parse legacy pipe-separated verify output

Output: Validation report (pass/fail checks).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from chrome_api import ChromeBookmarks, BookmarkNode


def validate_tree(roots: list[BookmarkNode]) -> dict:
    """Run validation checks on the live bookmark tree."""
    if not roots or not roots[0].children:
        return {"status": "FAIL", "issues": ["No bookmarks found"], "warnings": []}

    bar = roots[0].children[0] if len(roots[0].children) > 0 else None
    if not bar:
        return {"status": "FAIL", "issues": ["No bookmark bar"], "warnings": []}

    top_level = bar.children
    issues = []
    warnings = []

    if len(top_level) > 12:
        issues.append(
            f"Too many top-level items ({len(top_level)}). "
            "Consider consolidating into fewer categories."
        )

    for child in top_level:
        if child.is_folder and child.count_urls() == 0:
            warnings.append(f"Empty folder: '{child.title}'")
        if child.is_folder and child.count_urls() > 200:
            warnings.append(
                f"Very large folder: '{child.title}' ({child.count_urls()} items). "
                "Consider adding sub-categories."
            )

    total_urls = bar.count_urls()
    uncategorized_count = sum(1 for c in top_level if c.url)

    if uncategorized_count > 10:
        warnings.append(
            f"{uncategorized_count} uncategorized bookmarks directly in bookmark bar."
        )

    summary = []
    for child in top_level:
        if child.is_folder:
            summary.append(f"{child.title}: {child.count_urls()}")
        else:
            summary.append(f"[link] {child.title}")

    return {
        "status": "PASS" if not issues else "FAIL",
        "total_bookmarks": total_urls,
        "top_level_items": len(top_level),
        "uncategorized": uncategorized_count,
        "issues": issues,
        "warnings": warnings,
        "summary": summary,
    }


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--pipe":
        text = sys.argv[2]
        entries = text.strip().split("|")
        print(f"Parsed {len(entries)} entries from pipe output")
        return

    cb = ChromeBookmarks()
    tree = cb.get_tree()
    result = validate_tree(tree)

    print(f"Status: {result['status']}")
    print(f"Total bookmarks: {result['total_bookmarks']}")
    print(f"Top-level items: {result['top_level_items']}")
    print(f"Uncategorized in root: {result['uncategorized']}")

    if result["issues"]:
        print("\nIssues:")
        for issue in result["issues"]:
            print(f"  ✗ {issue}")

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"  ! {warning}")

    print("\nStructure:")
    for line in result["summary"]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
