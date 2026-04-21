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
  local backup_file="${1:-}"
  local auto_confirm="${2:-}"

  if [ -z "$backup_file" ]; then
    echo "ERROR: No backup file specified." >&2
    echo "Usage: $0 restore <backup_file> [--yes]" >&2
    exit 1
  fi

  if [ ! -f "$backup_file" ]; then
    echo "ERROR: Backup file not found: $backup_file" >&2
    exit 1
  fi

  check_chrome

  echo "Reading backup file..."
  local total
  total="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['total_items'])" "$backup_file")"
  local bk_date
  bk_date="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('date','unknown'))" "$backup_file")"
  echo "Backup contains $total items (created $bk_date)"

  echo ""
  echo "RESTORE PLAN:"
  echo "1. Read current bookmark tree"
  echo "2. Match each backed-up item by ID"
  echo "3. Move misplaced items back to their original parent"
  echo ""

  if [ "$auto_confirm" != "--yes" ] && [ "$auto_confirm" != "-y" ]; then
    read -p "Proceed with restore? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
      echo "Restore cancelled."
      exit 0
    fi
  else
    echo "Auto-confirmed (--yes flag)."
  fi

  # Write backup data to a temp file, then load in chunks via Chrome
  local tmp_restore
  tmp_restore="$(mktemp /tmp/bk_restore_XXXXXX.json)"
  python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
items = data['items']
relevant = [i for i in items if 'parentId' in i and i.get('parentId') != '0']
json.dump(relevant, open(sys.argv[2], 'w'), ensure_ascii=False)
print(len(relevant))
" "$backup_file" "$tmp_restore"

  local chunk_size=100
  local item_count
  item_count="$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$tmp_restore")"

  echo "Loading $item_count items into Chrome in chunks..."

  # Initialize restore array in Chrome
  chrome_js "window._bkRestore = []; document.title = 'init'; 'ok';" >/dev/null
  sleep 1

  # Load data in chunks to avoid AppleScript string limits
  local offset=0
  while [ "$offset" -lt "$item_count" ]; do
    local chunk_json
    chunk_json="$(python3 -c "
import json, sys
items = json.load(open(sys.argv[1]))
chunk = items[int(sys.argv[2]):int(sys.argv[2])+int(sys.argv[3])]
print(json.dumps(chunk, ensure_ascii=False))
" "$tmp_restore" "$offset" "$chunk_size")"

    chrome_js "
window._bkRestore = window._bkRestore.concat($chunk_json);
document.title = 'loaded:' + window._bkRestore.length;
'ok';
" >/dev/null
    sleep 1
    offset=$((offset + chunk_size))
  done

  echo "Loaded $(read_title)"
  rm -f "$tmp_restore"

  echo "Moving items to original parents..."
  chrome_js "
var items = window._bkRestore;
var moved = 0;
var errors = 0;
function processBatch(startIdx) {
  var batch = items.slice(startIdx, startIdx + 15);
  if (batch.length === 0) {
    document.title = 'restore-done:moved=' + moved + ',errors=' + errors;
    return;
  }
  var batchDone = 0;
  batch.forEach(function(item) {
    try {
      chrome.bookmarks.move(item.id, {parentId: item.parentId}, function() {
        moved++;
        batchDone++;
        if (batchDone === batch.length) {
          document.title = 'progress:' + moved + '/' + items.length;
          setTimeout(function() { processBatch(startIdx + 15); }, 50);
        }
      });
    } catch(e) {
      errors++;
      batchDone++;
      if (batchDone === batch.length) {
        document.title = 'progress:' + moved + '/' + items.length;
        setTimeout(function() { processBatch(startIdx + 15); }, 50);
      }
    }
  });
}
processBatch(0);
'restoring...';
" >/dev/null

  # Poll for completion
  local max_wait=120
  local waited=0
  while [ "$waited" -lt "$max_wait" ]; do
    sleep 3
    waited=$((waited + 3))
    local status
    status="$(osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "document.title"' 2>&1)"
    if echo "$status" | grep -q "restore-done"; then
      echo "  $status"
      break
    fi
    echo "  $status"
  done

  echo ""
  echo "Verifying..."
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
  restore)  cmd_restore "${2:-}" "${3:-}" ;;
  list)     cmd_list "${2:-}" ;;
  help|*)
    echo "Bookmark Backup & Restore"
    echo ""
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  backup [dir]           Save current bookmarks to JSON"
    echo "  restore <file> [--yes] Restore bookmarks from backup"
    echo "  list [dir]             List available backups"
    echo ""
    echo "Default backup directory: $DEFAULT_BACKUP_DIR"
    ;;
esac
