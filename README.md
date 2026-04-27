# Video Parser Skill

Parse video metadata from 小红书 (Xiaohongshu/RED), 抖音 (Douyin), and B站 (Bilibili) and save as markdown files.

## Supported Platforms

| Platform | URL Pattern | Method |
|----------|------------|--------|
| 小红书 | `xiaohongshu.com/explore/xxx` | Web Scraping |
| 抖音 | `douyin.com/video/xxx` | Web Scraping |
| B站 | `bilibili.com/video/BVxxx` | Public API |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic usage
python3 fetch_video.py --url "https://www.bilibili.com/video/BV1xx411c7XZ"

# Custom output directory
python3 fetch_video.py --url "https://..." --output "/path/to/save"

# Sanitize filename (remove invalid chars)
python3 fetch_video.py --url "https://..." --sanitize
```

## Output

Saves to `{title}.md` with YAML frontmatter:

```markdown
---
platform: B站
url: https://www.bilibili.com/video/BV1xx411c7XZ
title: 视频标题
tags: ['tag1', 'tag2']
publish_time: 2026-04-27 10:30:00
topic: 知识
---

# 视频标题

## 文案
视频描述...

## 标签
#tag1 #tag2
```

## Default Path

`/Users/xiaoxiongmiemie/Documents/Obsidian Vault/raw`

## License

MIT
