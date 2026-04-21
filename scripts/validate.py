#!/usr/bin/env python3
"""Validate bookmark structure after reorganization.

Usage:
    python validate.py <verify_output>

Input: The pipe-separated verify output from chrome_bookmarks.sh verify.
Output: Validation report (pass/fail checks).
"""

import sys


def parse_verify_output(text: str) -> list[dict]:
    """Parse the pipe-separated verify output into structured data."""
    entries = text.strip().split("|")
    folders = []
    current_parent = None

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        if entry.startswith("> "):
            name, count = entry[2:].rsplit(": ", 1)
            folders.append({
                "name": name.strip(),
                "count": int(count),
                "parent": current_parent,
                "level": 2,
            })
        else:
            name, count = entry.rsplit(": ", 1)
            current_parent = name.strip()
            folders.append({
                "name": name.strip(),
                "count": int(count),
                "parent": None,
                "level": 1,
            })

    return folders


def validate(folders: list[dict]) -> dict:
    """Run validation checks on the folder structure."""
    issues = []
    warnings = []

    top_level = [f for f in folders if f["level"] == 1]

    if len(top_level) > 12:
        issues.append(
            f"Too many top-level folders ({len(top_level)}). "
            "Consider consolidating into fewer categories."
        )

    for f in folders:
        if f["count"] == 0 and f["level"] == 1:
            warnings.append(f"Empty top-level folder: '{f['name']}'")
        if f["count"] > 200:
            warnings.append(
                f"Very large folder: '{f['name']}' ({f['count']} items). "
                "Consider adding sub-categories."
            )

    total = sum(f["count"] for f in top_level)

    uncategorized = [f for f in top_level if f["count"] == 0]

    return {
        "status": "PASS" if not issues else "FAIL",
        "total_bookmarks": total,
        "top_level_folders": len(top_level),
        "issues": issues,
        "warnings": warnings,
        "summary": [
            f"{f['name']}: {f['count']}"
            for f in top_level
        ],
    }


def main():
    if len(sys.argv) < 2:
        text = sys.stdin.read()
    else:
        text = sys.argv[1]

    folders = parse_verify_output(text)
    result = validate(folders)

    print(f"Status: {result['status']}")
    print(f"Total bookmarks: {result['total_bookmarks']}")
    print(f"Top-level folders: {result['top_level_folders']}")

    if result["issues"]:
        print("\nIssues:")
        for issue in result["issues"]:
            print(f"  ❌ {issue}")

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"  ⚠️  {warning}")

    print("\nStructure:")
    for line in result["summary"]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
