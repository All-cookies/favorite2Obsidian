"""小红书 (Xiaohongshu/RED) parser — Cookie + __INITIAL_STATE__"""
import json
import os
import re
import time
import urllib.request
import ssl
from typing import Optional

from parsers.base import BaseParser
from parsers.data import VideoMetadata


class XiaohongshuParser(BaseParser):
    """Parser for 小红书 (Xiaohongshu/RED) notes via Cookie + __INITIAL_STATE__"""

    PLATFORM_NAME = "小红书"
    COOKIES_PATH = os.path.expanduser("~/cookies.json")

    def __init__(self, cookies_path: str = ""):
        super().__init__()
        self.cookies_path = cookies_path or self.COOKIES_PATH
        self._cookie_str = ""  # Store for video download
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.xiaohongshu.com/",
        }

    def detect(self, url: str) -> bool:
        pattern = r"xiaohongshu\.com/(explore|discovery/item|note)/([a-zA-Z0-9]+)"
        return bool(re.search(pattern, url))

    def parse(self, url: str) -> VideoMetadata:
        """Parse 小红书 note metadata via Cookie + __INITIAL_STATE__"""
        note_id = self._extract_note_id(url)
        if not note_id:
            raise ValueError(f"Invalid 小红书 URL: {url}")

        # Check cookies
        cookie_str = self._load_cookies()
        if not cookie_str:
            raise ValueError(
                f"Cookies 未找到或已过期。请按以下步骤导出：\n"
                f"1. 在 Chrome 打开 xiaohongshu.com 并确认已登录\n"
                f"2. 打开 DevTools Console (F12)\n"
                f"3. 运行: copy(JSON.stringify(document.cookie.split('; ').map(c => {{\n"
                f"     const [name, ...rest] = c.split('=');\n"
                f"     return {{ name, value: rest.join('='), domain: '.xiaohongshu.com' }};\n"
                f"   }})))\n"
                f"4. 将剪贴板内容保存到 {self.COOKIES_PATH}"
            )
        self._cookie_str = cookie_str

        # Build full URL with note_id
        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"

        # Fetch page HTML with cookies
        html = self._fetch_page(page_url, cookie_str)

        # Check if we got the actual note (not a redirect/error page)
        if not re.search(r'__INITIAL_STATE__', html):
            raise ValueError(
                f"Cookie 已过期或请求被拦截（未获取到页面数据）。\n"
                f"请重新从 Chrome 导出 cookies 到 {self.COOKIES_PATH}"
            )

        # Parse __INITIAL_STATE__
        data = self._parse_initial_state(html)

        if not data:
            raise ValueError("无法从页面中解析帖子数据，可能 cookies 已过期。")

        return self._parse_metadata(url, data)

    def _extract_note_id(self, url: str) -> Optional[str]:
        """Extract note ID (24-char hex string) from URL"""
        patterns = [
            r"xiaohongshu\.com/explore/([a-f0-9]{24})",
            r"xiaohongshu\.com/discovery/item/([a-f0-9]{24})",
            r"xiaohongshu\.com/note/([a-f0-9]{24})",
            # Fallback: any alphanumeric ID
            r"xiaohongshu\.com/(?:explore|discovery/item|note)/([a-zA-Z0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _load_cookies(self) -> str:
        """Load cookies from file and return as cookie string"""
        if not os.path.exists(self.cookies_path):
            return ""

        try:
            with open(self.cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # Build cookie string
            parts = []
            for c in cookies:
                name = c.get("name", "")
                value = c.get("value", "")
                if name and value:
                    parts.append(f"{name}={value}")

            return "; ".join(parts)
        except (json.JSONDecodeError, OSError):
            return ""

    def _fetch_page(self, url: str, cookie_str: str) -> str:
        """Fetch page HTML with cookies using urllib (no external dependency)"""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url)
        req.add_header("Cookie", cookie_str)
        for key, val in self.headers.items():
            if key.lower() == "cookie":
                continue
            req.add_header(key, val)

        try:
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as e:
            raise ValueError(f"请求小红书页面失败: {e}")

    def _parse_initial_state(self, html: str) -> Optional[dict]:
        """Parse window.__INITIAL_STATE__ from HTML"""
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*</script>",
            html,
            re.DOTALL,
        )
        if not match:
            return None

        raw = match.group(1)
        # Replace undefined with null for valid JSON
        raw = raw.replace("undefined", "null")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"解析 __INITIAL_STATE__ JSON 失败: {e}")

        # Navigate to note data: data['note']['noteDetailMap'][<key>]['note']
        try:
            note_map = data.get("note", {}).get("noteDetailMap", {})
            if not note_map:
                return None
            # Take the first (and usually only) entry
            for note_data in note_map.values():
                note = note_data.get("note", {})
                if note:
                    return note
        except (AttributeError, TypeError):
            pass

        return None

    def _extract_video_url(self, note: dict) -> str:
        """Extract video stream URL from note data
        
        小红书视频结构:
        note.video.media.stream.h264[].masterUrl
        或 note.video.media.stream.h265[].masterUrl
        """
        video = note.get("video", {})
        media = video.get("media", {})
        stream = media.get("stream", {})
        
        # Try h264 first (more compatible)
        h264 = stream.get("h264", [])
        if h264 and isinstance(h264, list):
            for item in h264:
                url = item.get("masterUrl", "")
                if url:
                    return url
        
        # Try h265
        h265 = stream.get("h265", [])
        if h265 and isinstance(h265, list):
            for item in h265:
                url = item.get("masterUrl", "")
                if url:
                    return url
        
        # Try av1
        av1 = stream.get("av1", [])
        if av1 and isinstance(av1, list):
            for item in av1:
                url = item.get("masterUrl", "")
                if url:
                    return url
        
        # Fallback: video.media.videoUrl
        video_url = media.get("videoUrl", "")
        if video_url:
            return video_url
        
        return ""

    def _parse_metadata(self, url: str, note: dict) -> VideoMetadata:
        """Parse note data dict into VideoMetadata"""
        # Title
        title = note.get("title", "")

        # Description / caption
        desc = note.get("desc", "")

        # Author
        user = note.get("user", {})
        author = user.get("nickname", "")

        # Tags (tagList)
        tags = []
        tag_list = note.get("tagList", [])
        if isinstance(tag_list, list):
            for t in tag_list:
                if isinstance(t, dict):
                    name = t.get("name", "")
                    if name:
                        tags.append(name)
                elif isinstance(t, str):
                    tags.append(t)

        # Also extract #话题# from desc
        topic_tags = re.findall(r"#([^#\s]+?)(?:\s|$)", desc)
        for tag in topic_tags:
            if tag not in tags:
                tags.append(tag)

        # Publish time
        raw_time = note.get("time", 0)
        if isinstance(raw_time, (int, float)) and raw_time > 0:
            # xhs timestamps are in milliseconds
            if raw_time > 1e12:
                raw_time = raw_time / 1000
            publish_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(raw_time))
        else:
            publish_time = ""

        # Topic
        topic = ""
        core_topic = note.get("coreTopic", {})
        if isinstance(core_topic, dict):
            topic = core_topic.get("topicName", "") or core_topic.get("name", "")

        # IP location
        ip_location = note.get("ipLocation", "")

        # Interaction info (likes, collects, comments, shares)
        interact = note.get("interactInfo", {})
        stats = {}
        if isinstance(interact, dict):
            if interact.get("likedCount"):
                stats["点赞"] = interact["likedCount"]
            if interact.get("collectedCount"):
                stats["收藏"] = interact["collectedCount"]
            if interact.get("commentCount"):
                stats["评论"] = interact["commentCount"]
            if interact.get("shareCount"):
                stats["分享"] = interact["shareCount"]

        # Note type (video or image)
        note_type = note.get("type", "")

        # Video duration (from video.capa.duration in seconds)
        duration = 0
        video = note.get("video", {})
        capa = video.get("capa", {})
        if isinstance(capa, dict):
            duration = capa.get("duration", 0) or 0
        # Fallback: video.duration (milliseconds)
        if not duration:
            duration = video.get("duration", 0) or 0
            if duration > 1000:
                duration = int(duration / 1000)

        # Video URL
        video_url = self._extract_video_url(note)

        # Clean desc: remove #话题# markers
        clean_desc = re.sub(r"#([^#\s]+)#?", "", desc).strip()

        # Build caption: include ip_location if available
        caption_parts = []
        if clean_desc:
            caption_parts.append(clean_desc)
        if ip_location:
            caption_parts.append(f"📍 {ip_location}")
        caption = "\n".join(caption_parts)

        return VideoMetadata(
            platform=self.PLATFORM_NAME,
            url=url,
            title=self._clean_text(title),
            caption=self._clean_text(caption),
            tags=tags,
            publish_time=publish_time,
            topic=topic,
            author=author,
            duration=duration,
            stats=stats,
            video_url=video_url,
        )
