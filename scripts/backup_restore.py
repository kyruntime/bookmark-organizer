#!/usr/bin/env python3
"""Bookmark backup and restore via Chrome Bookmarks API.

Usage:
    python backup_restore.py backup [output_dir]
    python backup_restore.py restore <backup_file> [--yes]
    python backup_restore.py list [backup_dir]
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from chrome_api import ChromeBookmarks, ChromeError

DEFAULT_BACKUP_DIR = Path.home() / ".bookmark-organizer" / "backups"


def cmd_backup(output_dir: str | None = None):
    backup_dir = Path(output_dir) if output_dir else DEFAULT_BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)

    cb = ChromeBookmarks()
    print("Reading bookmark tree...")
    tree = cb.get_tree()

    items = []
    for root in tree:
        for node in root.walk():
            item = {"id": node.id, "title": node.title, "parentId": node.parent_id}
            if node.url:
                item["url"] = node.url
            items.append(item)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"bookmarks_{timestamp}.json"

    data = {
        "version": 1,
        "timestamp": timestamp,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_items": len(items),
        "items": items,
    }

    backup_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Backup saved: {backup_file} ({len(items)} items)")

    _cleanup_old_backups(backup_dir, keep=10)
    cb.cleanup()
    return str(backup_file)


def _cleanup_old_backups(backup_dir: Path, keep: int = 10):
    """Keep only the most recent N backups, delete older ones."""
    backups = sorted(backup_dir.glob("bookmarks_*.json"), key=lambda f: f.stat().st_mtime)
    if len(backups) <= keep:
        return
    for old in backups[: len(backups) - keep]:
        old.unlink()
        print(f"  Cleaned up old backup: {old.name}")


def cmd_restore(backup_file: str, auto_confirm: bool = False):
    path = Path(backup_file)
    if not path.exists():
        print(f"ERROR: Backup file not found: {backup_file}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    total = data["total_items"]
    bk_date = data.get("date", "unknown")
    print(f"Backup contains {total} items (created {bk_date})")

    items = [i for i in data["items"] if i.get("parentId") and i["parentId"] != "0"]
    print(f"\nRESTORE PLAN:")
    print(f"  - {len(items)} items to move back to original parents")
    print()

    if not auto_confirm:
        confirm = input("Proceed with restore? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Restore cancelled.")
            return

    cb = ChromeBookmarks()
    moved = 0
    errors = 0

    batch_size = 15
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        for item in batch:
            try:
                cb.move(item["id"], item["parentId"])
                moved += 1
            except ChromeError:
                errors += 1
        print(f"  progress: {moved + errors}/{len(items)}  (moved={moved}, errors={errors})")
        if i + batch_size < len(items):
            time.sleep(0.5)

    print(f"\nRestore complete: moved={moved}, errors={errors}")

    print("Verifying...")
    tree = cb.get_tree()
    total_verified = sum(1 for root in tree for _ in root.walk())
    print(f"Verified: {total_verified} items in tree")

    cb.cleanup()


def cmd_list(backup_dir: str | None = None):
    bd = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
    if not bd.exists():
        print(f"No backups found. Directory does not exist: {bd}")
        return

    print(f"Available backups in {bd}:\n")
    found = False
    for f in sorted(bd.glob("bookmarks_*.json")):
        found = True
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            size_kb = f.stat().st_size // 1024
            print(f"  {f.name}  |  {data.get('date', '?')}  |  {data['total_items']} items  |  {size_kb}KB")
        except (json.JSONDecodeError, KeyError):
            print(f"  {f.name}  (parse error)")

    if not found:
        print("  (no backups found)")


def main():
    if len(sys.argv) < 2:
        print("Bookmark Backup & Restore")
        print()
        print("Usage:")
        print(f"  {sys.argv[0]} backup [dir]            Save current bookmarks")
        print(f"  {sys.argv[0]} restore <file> [--yes]  Restore from backup")
        print(f"  {sys.argv[0]} list [dir]              List available backups")
        print()
        print(f"Default backup directory: {DEFAULT_BACKUP_DIR}")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "backup":
        result = cmd_backup(sys.argv[2] if len(sys.argv) > 2 else None)
        print(result)

    elif cmd == "restore":
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} restore <backup_file> [--yes]", file=sys.stderr)
            sys.exit(1)
        auto = "--yes" in sys.argv or "-y" in sys.argv
        cmd_restore(sys.argv[2], auto_confirm=auto)

    elif cmd == "list":
        cmd_list(sys.argv[2] if len(sys.argv) > 2 else None)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
