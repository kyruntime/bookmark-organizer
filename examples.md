# Usage Examples

## Example 1: Full Reorganization

**User**: "帮我整理一下 Chrome 书签"

**Agent workflow**:

1. Check prerequisites (Chrome running, JS Apple Events enabled)
2. Read bookmark tree via `chrome.bookmarks.getTree()`
3. Analyze: 640 bookmarks, 35 folders, many uncategorized
4. Propose:

```
Proposed structure:
├── 工作-随行付 (50 links)
│   ├── resto (26)
│   ├── 销售子系统 (14)
│   └── 供应链管理系统 (4)
├── 工作-233 (272 links)
│   ├── 233 (215)
│   ├── 文档服务器 (48)
│   └── 正式 (7)
├── 技术学习 (170 links)
│   ├── Java基础 (31)
│   ├── Spring生态 (21)
│   ├── 数据库 (15)
│   └── ...
├── AI & Cursor (20 links)
├── 日常工具 (10 links)
├── 生活 (73 links)
├── 归档 (41 links)
└── 小程序开发 (4 links)
```

5. User confirms → execute
6. Verify final structure

## Example 2: Find Duplicates

**User**: "Find duplicate bookmarks"

**Agent workflow**:

1. Scan all URLs, normalize (strip trailing slash)
2. Report:

```
Found 12 duplicate URLs:
1. https://github.com/settings — appears in "开发工具" and "日常工具"
2. https://docs.spring.io/... — appears in "Java" and "Spring"
...

Which duplicates should I remove? (I'll keep the copy in the more relevant folder)
```

3. User picks → agent removes selected copies

## Example 3: Incremental Organization

**User**: "把技术学习里的书签再细分一下"

**Agent workflow**:

1. Read children of "技术学习" folder
2. Analyze titles and URLs, suggest sub-categories
3. Propose:

```
技术学习 sub-categories:
├── Java基础 — items with "java", "jdk", "jvm" in title/URL
├── Spring生态 — spring.io, baeldung.com/spring-*
├── 数据库 — mysql, redis, mongodb related
├── 中间件 — kafka, rabbitmq, elasticsearch
├── 前端 — vue, react, css, html related
├── 开发工具 — git, docker, ide, postman
└── 博客与书籍 — blog posts, book references
```

4. User confirms → create sub-folders and move items
