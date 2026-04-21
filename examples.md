# Usage Examples

## Example 1: Full Reorganization

**User**: "帮我整理一下 Chrome 书签"

**Agent workflow**:

1. Check prerequisites (Chrome running, JS Apple Events enabled)
2. Read bookmark tree via `chrome.bookmarks.getTree()`
3. Analyze: 320 bookmarks, 18 folders, many uncategorized
4. Propose:

```
Proposed structure:
├── 工作-ProjectA (85 links)
│   ├── 后台管理 (40)
│   ├── API文档 (25)
│   └── 部署运维 (20)
├── 工作-ProjectB (60 links)
│   ├── 开发环境 (35)
│   └── 测试环境 (25)
├── 技术学习 (90 links)
│   ├── Java (25)
│   ├── 前端 (20)
│   ├── 数据库 (15)
│   └── 博客与教程 (30)
├── AI & 工具 (25 links)
├── 日常工具 (15 links)
├── 生活 (30 links)
│   ├── 购物 (12)
│   ├── 娱乐 (10)
│   └── 其他 (8)
└── 归档 (15 links)
```

5. User confirms → execute
6. Verify final structure

## Example 2: Find Duplicates

**User**: "Find duplicate bookmarks"

**Agent workflow**:

1. Scan all URLs, normalize (strip trailing slash)
2. Report:

```
Found 8 duplicate URLs:
1. https://github.com/settings — appears in "开发工具" and "日常"
2. https://docs.spring.io/spring-boot — appears in "Java" and "Spring"
3. https://mail.google.com — appears in root and "日常工具"
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
