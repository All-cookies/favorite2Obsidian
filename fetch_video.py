#!/usr/bin/env python3
"""
Video Parser CLI - Parse video metadata from 小红书, 抖音, B站
"""
import argparse
import sys
from pathlib import Path

# Add package root to path for imports
pkg_root = Path(__file__).parent
sys.path.insert(0, str(pkg_root))

from parsers import (
    VideoMetadata,
    XiaohongshuParser,
    DouyinParser,
    BilibiliParser,
)
from utils import generate_markdown, generate_outline, format_outline_markdown


DEFAULT_OUTPUT_DIR = "/Users/xiaoxiongmiemie/Documents/Obsidian Vault/raw"


def detect_platform(url: str):
    """Detect which platform the URL belongs to"""
    parsers = [
        XiaohongshuParser(),
        DouyinParser(),
        BilibiliParser(),
    ]

    for parser in parsers:
        if parser.detect(url):
            return parser

    return None


def parse_and_save(url: str, output_dir: str, sanitize: bool = False, transcribe: bool = False, overwrite: bool = False, outline: bool = False) -> str:
    """Parse video URL and save to markdown file
    
    Args:
        url: Video URL
        output_dir: Output directory for markdown file
        sanitize: Whether to sanitize filename
        transcribe: Whether to transcribe video audio (only for 小红书 videos)
        overwrite: If True, overwrite existing file with same title
        outline: If True, generate structured content outline from transcription
        
    Returns:
        Path to saved markdown file
    """
    parser = detect_platform(url)
    if not parser:
        raise ValueError(
            f"Unsupported URL. Supported platforms: 小红书, 抖音, B站\n"
            f"URL: {url}"
        )

    print(f"[+] Detected platform: {parser.PLATFORM_NAME}")

    metadata = parser.parse(url)
    print(f"[+] Title: {metadata.title}")
    
    # Transcribe video if requested and video URL is available
    if transcribe and metadata.video_url:
        print(f"[+] Video URL found, transcribing...")
        try:
            from utils.transcribe import transcribe_video
            
            # Get cookies for 小红书
            cookies = ""
            if hasattr(parser, "_cookie_str"):
                cookies = parser._cookie_str
            
            # Get referer for B站
            referer = ""
            if metadata.platform == "B站":
                referer = "https://www.bilibili.com/"
            
            transcription = transcribe_video(metadata.video_url, cookies=cookies, language="zh", referer=referer)
            metadata.transcription = transcription
            print(f"[+] Transcription: {transcription[:100]}...")
        except Exception as e:
            print(f"[!] Transcription failed: {e}")
    elif transcribe and not metadata.video_url:
        print(f"[!] No video URL found, skipping transcription")

    # Generate outline if requested and transcription is available
    outline_md = ""
    if outline and metadata.transcription:
        print(f"[+] Generating content outline...")
        try:
            outline_dict = generate_outline(metadata.transcription, title=metadata.title)
            outline_md = format_outline_markdown(outline_dict)
            print(f"[+] Outline: {len(outline_dict.get('topics', []))} topics, {len(outline_dict.get('summary', []))} summary points")
        except Exception as e:
            print(f"[!] Outline generation failed: {e}")
    elif outline and not metadata.transcription:
        print(f"[!] No transcription available, need --transcribe first")

    filepath = generate_markdown(metadata, output_dir, sanitize=sanitize, overwrite=overwrite, outline_md=outline_md)
    print(f"[+] Saved to: {filepath}")

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Parse video metadata from 小红书, 抖音, B站 to markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_video.py --url "https://www.bilibili.com/video/BV1xx411c7XZ"
  python3 fetch_video.py --url "https://www.douyin.com/video/xxx" --output "/path/to/save"
  python3 fetch_video.py --url "https://www.xiaohongshu.com/explore/xxx" --sanitize
  python3 fetch_video.py --url "https://www.xiaohongshu.com/explore/xxx" --transcribe
        """,
    )

    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Video URL from 小红书, 抖音, or B站",
    )

    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )

    parser.add_argument(
        "--sanitize", "-s",
        action="store_true",
        help="Sanitize filename (remove invalid characters)",
    )

    parser.add_argument(
        "--transcribe", "-t",
        action="store_true",
        help="Transcribe video audio to text (requires faster-whisper, supports 小红书 and B站)",
    )

    parser.add_argument(
        "--overwrite", "-w",
        action="store_true",
        help="Overwrite existing file with same title (no duplicate _1, _2 suffixes)",
    )

    parser.add_argument(
        "--outline",
        action="store_true",
        help="Generate structured content outline (requires --transcribe)",
    )

    args = parser.parse_args()

    try:
        filepath = parse_and_save(args.url, args.output, sanitize=args.sanitize, transcribe=args.transcribe, overwrite=args.overwrite, outline=args.outline)
        print(f"\n[SUCCESS] File saved: {filepath}")
        return 0
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
