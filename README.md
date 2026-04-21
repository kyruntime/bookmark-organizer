# Bookmark Organizer

一个 AI Agent Skill，通过自然语言对话智能整理浏览器书签 —— 分析、分类、去重、重组你的书签收藏。

## 功能清单

| 功能 | 状态 | 说明 |
|------|------|------|
| **智能分析** | ✅ | 分析书签标题、URL、域名，自动推荐分类方案 |
| **交互式规划** | ✅ | 展示拟定结构，用户确认后再执行 |
| **创建与移动** | ✅ | 通过 Chrome Bookmarks API 创建文件夹、移动书签 |
| **去重检测** | ✅ | 检测并合并重复的 URL（支持 http/https 归一化） |
| **死链检查** | 🚧 | 识别已失效的链接（404） |
| **备份与回滚** | ✅ | 操作前自动快照，不满意可一键恢复到之前的状态 |
| **多浏览器** | 🔜 | 目前支持 Chrome（macOS）；Safari、Firefox、Edge 计划中 |

## 工作原理

```
┌──────────────────────────────────────────────────────┐
│  用户: "帮我整理一下书签"                               │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  1. 读取: 通过 AppleScript 调用 chrome.bookmarks API  │
│     获取完整书签树                                     │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  2. 分析: 统计数量，识别域名聚类，                       │
│     基于 URL 模式和标题推荐分类                         │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  3. 规划: 向用户展示拟定的文件夹结构和数量               │
│     用户确认或调整后再执行                              │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  4. 执行: 创建文件夹，移动书签，清理空文件夹             │
│     全部通过浏览器原生 API 操作                         │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  5. 验证: 展示最终结构和各分类数量                      │
└──────────────────────────────────────────────────────┘
```

## 前提条件

- **macOS**（使用 AppleScript 与 Chrome 通信）
- **Google Chrome** 并开启「允许 Apple 事件中的 JavaScript」
  - Chrome 菜单 → 视图 → 开发者 → 允许 Apple 事件中的 JavaScript
- Chrome 需要正在运行，并至少打开一个标签页

## 安装

### 一键安装（推荐）

```bash
git clone https://github.com/YOUR_USERNAME/bookmark-organizer.git
cd bookmark-organizer

# 安装到 Cursor
./install.sh --cursor

# 安装到 Claude Code
./install.sh --claude

# 安装到所有支持的平台
./install.sh --all
```

`install.sh` 会创建符号链接到 `~/.cursor/skills/`（或对应平台目录），后续更新代码自动生效。

### 手动安装

```bash
# Cursor
cp -r bookmark-organizer ~/.cursor/skills/

# Claude Code
cp -r bookmark-organizer ~/.claude/skills/
```

## 使用方式

直接对 AI Agent 说：

- "帮我整理一下 Chrome 书签"
- "Help me organize my Chrome bookmarks"
- "找出重复的书签"
- "检查有没有失效的书签链接"
- "把技术学习里的书签再细分一下"

Agent 会根据 Skill 描述中的触发词自动加载此技能。

## 项目结构

```
bookmark-organizer/
├── SKILL.md                   # 技能主文件（Cursor/Claude Code/OpenClaw 通用）
├── README.md                  # 本文件
├── install.sh                 # 一键安装脚本
├── examples.md                # 使用示例
├── scripts/
│   ├── chrome_api.py          # Python 核心库（推荐）
│   ├── chrome_bookmarks.sh    # Shell 封装（轻量场景）
│   ├── backup_restore.sh      # 备份与一键恢复
│   ├── analyze.py             # 书签分析与分类建议
│   ├── validate.py            # 整理后的结构验证
│   └── smoke_test.py          # 冒烟测试
└── .gitignore
```

## 备份与恢复

整理前 Agent 会**自动创建备份**，如果不满意可以一键恢复。你也可以手动操作：

```bash
# 创建备份（保存到 ~/.bookmark-organizer/backups/）
bash scripts/backup_restore.sh backup

# 查看所有备份
bash scripts/backup_restore.sh list

# 恢复到某个备份（交互式确认）
bash scripts/backup_restore.sh restore ~/.bookmark-organizer/backups/bookmarks_20260421_143000.json

# 跳过确认直接恢复（Agent 调用时使用）
bash scripts/backup_restore.sh restore <backup_file> --yes
```

备份文件记录了每个书签的 ID、标题、URL 和所属文件夹，恢复时通过 `chrome.bookmarks.move()` 把每个书签移回原位。

## 去重检测

```bash
# 扫描重复书签
python3 scripts/chrome_api.py dupes
```

支持 URL 归一化（忽略 trailing slash、http/https 差异），找到重复后展示给用户确认再删除。

## 验证安装

运行冒烟测试确认一切正常（需要 Chrome 运行中）：

```bash
cd bookmark-organizer
python3 scripts/smoke_test.py
```

预期输出 `Results: 6/6 passed`。脚本会自动导航到 `chrome://bookmarks` 页面（API 仅在该页面可用）。

## 技术原理

直接修改 Chrome 的 `Bookmarks` JSON 文件是不可靠的 —— Chrome 的云同步会把改动覆盖回去。

本 Skill 使用 **AppleScript → Chrome JavaScript 执行** 的方式调用 `chrome.bookmarks.*` API，Chrome 会将其视为内部操作并正确同步。

核心 API 调用：
- `chrome.bookmarks.getTree()` — 读取完整书签树
- `chrome.bookmarks.create({parentId, title})` — 创建文件夹
- `chrome.bookmarks.move(id, {parentId})` — 移动书签
- `chrome.bookmarks.remove(id)` / `removeTree(id)` — 删除
- `chrome.bookmarks.search({url})` — 搜索/查重

## 贡献

欢迎 PR！以下方向特别需要帮助：
- Windows / Linux 支持（需要不同的浏览器自动化方案）
- Safari、Firefox、Edge 浏览器支持
- 更智能的基于 ML 的分类
- 链接健康检查（批量验证 URL 有效性）

## 许可证

MIT
