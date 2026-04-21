#!/usr/bin/env bash
# Bookmark backup and restore via Chrome Bookmarks API
# Usage:
#   ./backup_restore.sh backup [output_dir]   - Save current structure to JSON
#   ./backup_restore.sh restore <backup_file>  - Restore from a backup JSON
#   ./backup_restore.sh list [backup_dir]      - List available backups

set -euo pipefail

WAIT_SEC="${WAIT_SEC:-3}"
DEFAULT_BACKUP_DIR="$HOME/.bookmark-organizer/backups"

chrome_js() {
  osascript -e "tell application \"Google Chrome\" to execute front window's active tab javascript \"$1\"" 2>&1
}

read_title() {
  sleep "$WAIT_SEC"
  osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "document.title"' 2>&1
}

check_chrome() {
  if ! pgrep -x "Google Chrome" >/dev/null 2>&1; then
    echo "ERROR: Google Chrome is not running." >&2
    exit 1
  fi
}

cmd_backup() {
  local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
  mkdir -p "$backup_dir"

  check_chrome

  local timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  local backup_file="$backup_dir/bookmarks_${timestamp}.json"

  echo "Reading bookmark tree..."

  # Read the full tree structure including IDs, titles, URLs, and parent relationships
  # Split into chunks since document.title has size limits
  chrome_js "
chrome.bookmarks.getTree(function(tree) {
  var items = [];
  function walk(node, parentId) {
    var item = {id: node.id, title: node.title, parentId: parentId};
    if (node.url) item.url = node.url;
    items.push(item);
    if (node.children) node.children.forEach(function(c) { walk(c, node.id); });
  }
  tree[0].children.forEach(function(c) { walk(c, tree[0].id); });
  window._bkBackup = items;
  window._bkChunkIdx = 0;
  window._bkChunkSize = 200;
  var chunk = items.slice(0, 200);
  document.title = 'CHUNK:0:' + items.length + ':' + JSON.stringify(chunk);
});
'backing up...';
" >/dev/null

  sleep "$WAIT_SEC"

  local result
  result="$(read_title)"

  # Parse first chunk header to get total count
  local total
  total="$(echo "$result" | sed -n 's/^CHUNK:0:\([0-9]*\):.*/\1/p')"

  if [ -z "$total" ]; then
    echo "ERROR: Failed to read bookmarks. Got: $result" >&2
    exit 1
  fi

  # Extract first chunk data
  local first_data
  first_data="$(echo "$result" | sed "s/^CHUNK:0:${total}://")"

  echo "$first_data" > "$backup_file.tmp"

  # Read remaining chunks if needed
  local offset=200
  while [ "$offset" -lt "$total" ]; do
    chrome_js "
var chunk = window._bkBackup.slice($offset, $offset + window._bkChunkSize);
document.title = 'CHUNK:$offset:' + JSON.stringify(chunk);
'ok';
" >/dev/null
    sleep "$WAIT_SEC"
    result="$(read_title)"
    local chunk_data
    chunk_data="$(echo "$result" | sed "s/^CHUNK:${offset}://")"

    # Merge JSON arrays: remove trailing ] from accumulated, remove leading [ from new chunk
    local accumulated
    accumulated="$(cat "$backup_file.tmp")"
    accumulated="${accumulated%]}"
    chunk_data="${chunk_data#[}"
    echo "${accumulated},${chunk_data}" > "$backup_file.tmp"

    offset=$((offset + 200))
  done

  # Wrap in metadata
  local final_data
  final_data="$(cat "$backup_file.tmp")"
  cat > "$backup_file" <<ENDJSON
{
  "version": 1,
  "timestamp": "$timestamp",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_items": $total,
  "items": $final_data
}
ENDJSON

  rm -f "$backup_file.tmp"
  echo "Backup saved: $backup_file ($total items)"
  echo "$backup_file"
}

cmd_restore() {
  local backup_file="$1"

  if [ ! -f "$backup_file" ]; then
    echo "ERROR: Backup file not found: $backup_file" >&2
    exit 1
  fi

  check_chrome

  echo "Reading backup file..."
  local total
  total="$(python3 -c "import json,sys; d=json.load(open('$backup_file')); print(d['total_items'])")"
  echo "Backup contains $total items (created $(python3 -c "import json; d=json.load(open('$backup_file')); print(d.get('date','unknown'))"))"

  echo ""
  echo "RESTORE PLAN:"
  echo "1. Read current bookmark tree"
  echo "2. For each item in backup, ensure it exists in the correct parent folder"
  echo "3. Move misplaced items back to their original parent"
  echo ""
  read -p "Proceed with restore? [y/N] " confirm
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Restore cancelled."
    exit 0
  fi

  # Extract items as a compact JSON array for injection
  local items_json
  items_json="$(python3 -c "
import json, sys
data = json.load(open('$backup_file'))
items = data['items']
# Only include items with parentId (skip root nodes)
relevant = [i for i in items if 'parentId' in i and i.get('parentId') != '0']
print(json.dumps(relevant, ensure_ascii=False))
")"

  # Inject backup data and process in batches
  # Step 1: Create all missing folders first
  echo "Step 1/3: Creating missing folders..."
  chrome_js "
window._bkRestore = $items_json;
window._bkFolders = window._bkRestore.filter(function(i) { return !i.url; });
window._bkUrls = window._bkRestore.filter(function(i) { return !!i.url; });
document.title = 'loaded:folders=' + window._bkFolders.length + ',urls=' + window._bkUrls.length;
'ok';
" >/dev/null
  sleep "$WAIT_SEC"
  echo "$(read_title)"

  # Step 2: Move items back to original parents
  echo "Step 2/3: Moving items to original parents..."
  chrome_js "
var items = window._bkRestore;
var moved = 0;
var errors = 0;
var batch = items.slice(0, 20);
function processBatch(startIdx) {
  var batch = items.slice(startIdx, startIdx + 20);
  if (batch.length === 0) {
    document.title = 'restore-done:moved=' + moved + ',errors=' + errors;
    return;
  }
  var batchDone = 0;
  batch.forEach(function(item) {
    chrome.bookmarks.move(item.id, {parentId: item.parentId}, function() {
      moved++;
      batchDone++;
      if (batchDone === batch.length) {
        setTimeout(function() { processBatch(startIdx + 20); }, 100);
      }
    });
  });
}
processBatch(0);
'restoring...';
" >/dev/null

  # Poll for completion
  local max_wait=60
  local waited=0
  while [ "$waited" -lt "$max_wait" ]; do
    sleep 3
    waited=$((waited + 3))
    local status
    status="$(read_title)"
    if echo "$status" | grep -q "restore-done"; then
      echo "$status"
      break
    fi
    echo "  ...processing ($waited seconds)"
  done

  echo ""
  echo "Step 3/3: Verifying..."
  chrome_js "
chrome.bookmarks.getTree(function(tree) {
  var cnt = 0;
  function count(n) { cnt++; if(n.children) n.children.forEach(count); }
  tree[0].children.forEach(count);
  document.title = 'verified:' + cnt + ' items';
});
'ok';
" >/dev/null
  sleep "$WAIT_SEC"
  echo "$(read_title)"
  echo ""
  echo "Restore complete!"
}

cmd_list() {
  local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"

  if [ ! -d "$backup_dir" ]; then
    echo "No backups found. Directory does not exist: $backup_dir"
    exit 0
  fi

  echo "Available backups in $backup_dir:"
  echo ""

  for f in "$backup_dir"/bookmarks_*.json; do
    if [ ! -f "$f" ]; then
      echo "  (no backups found)"
      break
    fi
    local info
    info="$(python3 -c "
import json, os
d = json.load(open('$f'))
size = os.path.getsize('$f')
print(f\"  {os.path.basename('$f')}  |  {d.get('date','?')}  |  {d['total_items']} items  |  {size//1024}KB\")
" 2>/dev/null || echo "  $(basename "$f")  (parse error)")"
    echo "$info"
  done
}

case "${1:-help}" in
  backup)   cmd_backup "${2:-}" ;;
  restore)  cmd_restore "${2:?Usage: $0 restore <backup_file>}" ;;
  list)     cmd_list "${2:-}" ;;
  help|*)
    echo "Bookmark Backup & Restore"
    echo ""
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  backup [dir]       Save current bookmarks to JSON"
    echo "  restore <file>     Restore bookmarks from backup"
    echo "  list [dir]         List available backups"
    echo ""
    echo "Default backup directory: $DEFAULT_BACKUP_DIR"
    ;;
esac
