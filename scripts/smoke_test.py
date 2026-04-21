#!/usr/bin/env python3
"""Smoke test for bookmark-organizer skill.

Runs through the core workflow to verify everything works:
1. Check Chrome is running and JS Apple Events is enabled
2. Read bookmark tree
3. Get summary
4. Check for duplicates
5. Create a test folder, then delete it

Usage:
    python3 scripts/smoke_test.py

Exit codes:
    0 = all tests passed
    1 = one or more tests failed
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from chrome_api import ChromeBookmarks, ChromeError


def test(name: str, func):
    """Run a test and print result."""
    try:
        result = func()
        print(f"  PASS  {name}")
        return result
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        return None


def main():
    print("Bookmark Organizer — Smoke Test")
    print("=" * 50)

    cb = ChromeBookmarks(wait=2)
    passed = 0
    failed = 0
    total = 0

    # Test 1: Chrome running
    total += 1
    try:
        cb.check_chrome_running()
        print("  PASS  Chrome is running")
        passed += 1
    except ChromeError as e:
        print(f"  FAIL  Chrome check: {e}")
        print("\nCannot continue without Chrome. Exiting.")
        sys.exit(1)

    # Test 2: Read tree
    total += 1
    tree = test("Read bookmark tree", lambda: cb.get_tree())
    if tree is not None:
        passed += 1
        total_urls = sum(r.count_urls() for r in tree)
        print(f"         → {total_urls} bookmarks, {len(tree)} root nodes")
    else:
        failed += 1
        print("\nCannot continue without tree access. Exiting.")
        sys.exit(1)

    # Test 3: Summary
    total += 1
    summary = test("Get summary", lambda: cb.get_summary())
    if summary is not None:
        passed += 1
        bar_count = len(summary.get("bookmark_bar", []))
        print(f"         → {bar_count} top-level items in bookmark bar")
    else:
        failed += 1

    # Test 4: Duplicates
    total += 1
    dupes = test("Find duplicates", lambda: cb.find_duplicates())
    if dupes is not None:
        passed += 1
        print(f"         → {len(dupes)} duplicate URL groups found")
    else:
        failed += 1

    # Test 5: Create and delete a test folder
    total += 1
    bar_id = None
    if tree and len(tree) > 0 and len(tree[0].children) > 0:
        bar_id = tree[0].children[0].id

    if bar_id:
        def create_and_delete():
            test_id = cb.create_folder(bar_id, "__smoke_test_folder__")
            assert test_id, "Failed to create folder"
            ok = cb.remove(test_id)
            assert ok, "Failed to remove folder"
            return test_id

        result = test("Create + delete test folder", create_and_delete)
        if result:
            passed += 1
        else:
            failed += 1
    else:
        print("  SKIP  Create + delete test folder (no bookmark bar found)")

    # Test 6: Get children
    total += 1
    if bar_id:
        children = test("Get children of bookmark bar", lambda: cb.get_children(bar_id))
        if children is not None:
            passed += 1
            print(f"         → {len(children)} children")
        else:
            failed += 1
    else:
        print("  SKIP  Get children (no bookmark bar found)")

    print("=" * 50)
    print(f"Results: {passed}/{total} passed, {total - passed} failed")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
