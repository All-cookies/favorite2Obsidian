---
name: video-parser-skill
description: "Parse video metadata from 小红书 (Xiaohongshu/RED), 抖音 (Douyin), and B站 (Bilibili). Extract title, caption, tags, publish time, and topic. Save as markdown file. Use when user shares a video URL and wants to save structured metadata."
---

# Video Parser Skill

Parse video metadata from Chinese social platforms and save to markdown files.

---

## Supported Platforms

| Platform | URL Pattern | Parse Method |
|----------|------------|-------------|
| 小红书 | `xiaohongshu.com/explore/xxx` | Web scraping |
| 抖音 | `douyin.com/video/xxx` | Web scraping |
| B站 | `bilibili.com/video/BVxxx` | Public API |

---

## Usage

### CLI
```bash
# Basic usage
python3 fetch_video.py --url "https://www.bilibili.com/video/BV1xx411c7XZ"

# Custom output path
python3 fetch_video.py --url "https://..." --output "/path/to/save"

# Sanitize filename
python3 fetch_video.py --url "https://..." --sanitize
```

### Integration with OpenClaw
```
user:帮我解析这个视频 https://www.bilibili.com/video/BV1xx411c7XZ
agent: 执行 fetch_video.py --url "https://www.bilibili.com/video/BV1xx411c7XZ"
```

---

## Output Format

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
视频的完整描述文案...

## 标签
#tag1 #tag2
```

---

## Default Save Path

`/Users/xiaoxiongmiemie/Documents/Obsidian Vault/raw`

Filename: `{title}.md`

---

## Requirements

- Python 3.8+
- `pip install -r requirements.txt`
