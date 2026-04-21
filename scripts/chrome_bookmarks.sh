#!/usr/bin/env bash
# Chrome Bookmarks API wrapper via AppleScript
# Usage: ./chrome_bookmarks.sh <command> [args...]
#
# Commands:
#   tree          - Print full bookmark tree
#   children ID   - List children of folder ID
#   create PID TITLE - Create folder under parent ID
#   move ID PID   - Move bookmark ID to parent folder PID
#   remove ID     - Remove bookmark (or folder tree)
#   search QUERY  - Search bookmarks by title/URL
#   dupes         - Find duplicate URLs
#   verify        - Show top-level structure with counts

set -euo pipefail

WAIT_SEC="${WAIT_SEC:-2}"

chrome_js() {
  local js="$1"
  osascript -e "tell application \"Google Chrome\" to execute front window's active tab javascript \"$js\"" 2>&1
}

read_title() {
  sleep "$WAIT_SEC"
  osascript -e 'tell application "Google Chrome" to execute front window'\''s active tab javascript "document.title"' 2>&1
}

check_chrome() {
  if ! pgrep -x "Google Chrome" >/dev/null 2>&1; then
    echo "ERROR: Google Chrome is not running." >&2
    echo "Please open Chrome and try again." >&2
    exit 1
  fi
}

cmd_tree() {
  check_chrome
  chrome_js "
chrome.bookmarks.getTree(function(tree) {
  var bar = tree[0].children[0];
  var lines = [];
  function walk(node, depth) {
    var prefix = '';
    for(var i=0;i<depth;i++) prefix += '  ';
    if (node.url) {
      lines.push(prefix + '[' + node.id + '] ' + node.title + ' | ' + node.url);
    } else {
      var cnt = 0;
      function count(n) { if(n.url) cnt++; else if(n.children) n.children.forEach(count); }
      count(node);
      lines.push(prefix + '[' + node.id + '] F ' + node.title + ' (' + cnt + ')');
      if (node.children) node.children.forEach(function(c) { walk(c, depth+1); });
    }
  }
  bar.children.forEach(function(c) { walk(c, 0); });
  document.title = JSON.stringify(lines);
});
'reading...';
" >/dev/null
  read_title
}

cmd_children() {
  local folder_id="$1"
  check_chrome
  chrome_js "
chrome.bookmarks.getChildren('$folder_id', function(children) {
  var lines = children.map(function(c) {
    return c.url ? c.id+'|'+c.title+'|'+c.url : c.id+'|F|'+c.title;
  });
  document.title = JSON.stringify(lines);
});
'ok';
" >/dev/null
  read_title
}

cmd_create() {
  local parent_id="$1"
  local title="$2"
  check_chrome
  chrome_js "
chrome.bookmarks.create({parentId: '$parent_id', title: '$title'}, function(f) {
  document.title = 'created:' + f.id;
});
'ok';
" >/dev/null
  read_title
}

cmd_move() {
  local bookmark_id="$1"
  local parent_id="$2"
  check_chrome
  chrome_js "
chrome.bookmarks.move('$bookmark_id', {parentId: '$parent_id'}, function() {
  document.title = 'moved:$bookmark_id';
});
'ok';
" >/dev/null
  read_title
}

cmd_remove() {
  local bookmark_id="$1"
  check_chrome
  chrome_js "
chrome.bookmarks.removeTree('$bookmark_id', function() {
  document.title = 'removed:$bookmark_id';
});
'ok';
" >/dev/null
  read_title
}

cmd_search() {
  local query="$1"
  check_chrome
  chrome_js "
chrome.bookmarks.search('$query', function(results) {
  var lines = results.slice(0,100).map(function(r) {
    return r.id + '|' + r.title + '|' + (r.url||'FOLDER');
  });
  document.title = JSON.stringify(lines);
});
'ok';
" >/dev/null
  read_title
}

cmd_dupes() {
  check_chrome
  chrome_js "
chrome.bookmarks.getTree(function(tree) {
  var urls = {};
  var dupes = [];
  function walk(node) {
    if (node.url) {
      var u = node.url.replace(/\\\\/$/,'');
      if (urls[u]) {
        dupes.push(node.id + '|' + urls[u] + '|' + u.substring(0,120));
      } else {
        urls[u] = node.id;
      }
    }
    if (node.children) node.children.forEach(walk);
  }
  tree[0].children.forEach(walk);
  document.title = 'dupes:' + dupes.length + '|' + dupes.slice(0,50).join(';');
});
'scanning...';
" >/dev/null
  read_title
}

cmd_verify() {
  check_chrome
  chrome_js "
chrome.bookmarks.getTree(function(tree) {
  var bar = tree[0].children[0];
  var lines = [];
  bar.children.forEach(function(c) {
    var cnt = 0;
    function count(n) { if(n.url) cnt++; else if(n.children) n.children.forEach(count); }
    count(c);
    lines.push(c.title + ': ' + cnt);
    if (c.children) {
      c.children.forEach(function(sub) {
        if (!sub.url) {
          var scnt = 0;
          function scount(n) { if(n.url) scnt++; else if(n.children) n.children.forEach(scount); }
          scount(sub);
          lines.push('  > ' + sub.title + ': ' + scnt);
        }
      });
    }
  });
  document.title = lines.join('|');
});
'ok';
" >/dev/null
  read_title
}

case "${1:-help}" in
  tree)     cmd_tree ;;
  children) cmd_children "${2:?Usage: $0 children FOLDER_ID}" ;;
  create)   cmd_create "${2:?Usage: $0 create PARENT_ID TITLE}" "${3:?}" ;;
  move)     cmd_move "${2:?Usage: $0 move BOOKMARK_ID PARENT_ID}" "${3:?}" ;;
  remove)   cmd_remove "${2:?Usage: $0 remove BOOKMARK_ID}" ;;
  search)   cmd_search "${2:?Usage: $0 search QUERY}" ;;
  dupes)    cmd_dupes ;;
  verify)   cmd_verify ;;
  help|*)
    echo "Chrome Bookmarks CLI"
    echo ""
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  tree              Print full bookmark tree"
    echo "  children ID       List children of folder"
    echo "  create PID TITLE  Create folder under parent"
    echo "  move ID PID       Move bookmark to folder"
    echo "  remove ID         Remove bookmark/folder"
    echo "  search QUERY      Search by title/URL"
    echo "  dupes             Find duplicate URLs"
    echo "  verify            Show structure summary"
    echo ""
    echo "Environment:"
    echo "  WAIT_SEC=2        Seconds to wait for Chrome callback"
    ;;
esac
