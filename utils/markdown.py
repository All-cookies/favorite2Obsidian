"""Markdown file generator"""
import os
import re
from pathlib import Path
from typing import Optional

from parsers.data import VideoMetadata


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Sanitize title to be a valid filename"""
    if not title:
        title = "untitled"

    # Replace invalid chars with underscore
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(invalid_chars, "_", title)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Truncate to max length (but not in middle of word)
    if len(filename) > max_length:
        filename = filename[:max_length].rsplit(" ", 1)[0]

    return filename or "untitled"


def generate_markdown(metadata: VideoMetadata, output_dir: str, sanitize: bool = False, overwrite: bool = False, outline_md: str = "") -> str:
    """Generate markdown file from video metadata

    Returns the path to the created file.
    
    Args:
        metadata: Video metadata
        output_dir: Output directory
        sanitize: Whether to sanitize filename
        overwrite: If True, overwrite existing file with same title
        outline_md: Pre-formatted outline markdown to include
    """
    title = metadata.title
    if sanitize:
        title = sanitize_filename(title)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"{title}.md"
    filepath = output_path / filename

    # Handle duplicate filenames
    if not overwrite:
        counter = 1
        while filepath.exists():
            new_filename = f"{title}_{counter}.md"
            filepath = output_path / new_filename
            counter += 1

    # Build markdown content
    content = _build_markdown_content(metadata, outline_md=outline_md)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return str(filepath)


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS"""
    if not seconds or seconds <= 0:
        return ""
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _format_number(n) -> str:
    """Format large numbers for display (handles both int and str input)"""
    try:
        n = int(n)
    except (ValueError, TypeError):
        return str(n)
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def _build_markdown_content(metadata: VideoMetadata, outline_md: str = "") -> str:
    """Build markdown content from metadata"""
    # Frontmatter
    lines = [
        "---",
        f"platform: {metadata.platform}",
        f"url: {metadata.url}",
        f"title: {metadata.title}",
    ]

    if metadata.author:
        lines.append(f"author: {metadata.author}")

    if metadata.tags:
        tags_str = "[" + ", ".join(f"'{t}'" for t in metadata.tags) + "]"
        lines.append(f"tags: {tags_str}")

    if metadata.publish_time:
        lines.append(f"publish_time: {metadata.publish_time}")

    if metadata.topic:
        lines.append(f"topic: {metadata.topic}")

    if metadata.duration:
        lines.append(f"duration: {_format_duration(metadata.duration)}")

    if metadata.stats:
        stats_str = "{" + ", ".join(f"'{k}': '{_format_number(v)}'" for k, v in metadata.stats.items()) + "}"
        lines.append(f"stats: {stats_str}")

    lines.append("---")
    lines.append("")

    # Title
    lines.append(f"# {metadata.title}")
    lines.append("")

    # Author + publish info line
    info_parts = []
    if metadata.author:
        info_parts.append(f"UP主: {metadata.author}")
    if metadata.publish_time:
        info_parts.append(f"发布: {metadata.publish_time}")
    if metadata.duration:
        info_parts.append(f"时长: {_format_duration(metadata.duration)}")
    if info_parts:
        lines.append(" | ".join(info_parts))
        lines.append("")

    # Stats line
    if metadata.stats:
        stat_parts = [f"{k}: {_format_number(v)}" for k, v in metadata.stats.items()]
        lines.append(" | ".join(stat_parts))
        lines.append("")

    # Caption (文案)
    if metadata.caption:
        lines.append("## 文案")
        lines.append(metadata.caption)
        lines.append("")

    # Content Outline (内容大纲)
    if outline_md:
        lines.append(outline_md)

    # Tags (标签)
    if metadata.tags:
        lines.append("## 标签")
        tag_links = " ".join(f"#{tag}" for tag in metadata.tags)
        lines.append(tag_links)
        lines.append("")

    # Topic (主题)
    if metadata.topic:
        lines.append("## 主题")
        lines.append(metadata.topic)
        lines.append("")

    # Transcription (视频转写) - 放在最后
    if metadata.transcription:
        lines.append("## 视频转写")
        lines.append(metadata.transcription)
        lines.append("")

    return "\n".join(lines)
