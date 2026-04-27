"""抖音 (Douyin) parser"""
import json
import re
import time
from typing import Optional, Dict, Any

import requests

from parsers.base import BaseParser
from parsers.data import VideoMetadata


class DouyinParser(BaseParser):
    """Parser for 抖音 (Douyin) videos"""

    PLATFORM_NAME = "抖音"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.douyin.com/",
        }

    def detect(self, url: str) -> bool:
        patterns = [
            r"douyin\.com/video/(\d+)",
            r"www\.douyin\.com/video/(\d+)",
            r"v\.douyin\.com/[a-zA-Z0-9]+",
        ]
        return any(re.search(p, url) for p in patterns)

    def parse(self, url: str) -> VideoMetadata:
        """Parse 抖音 video metadata"""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"Invalid 抖音 URL: {url}")

        data = self._fetch_video_data(video_id)
        return self._parse_metadata(url, data)

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"douyin\.com/video/(\d+)",
            r"www\.douyin\.com/video/(\d+)",
            r"v\.douyin\.com/([a-zA-Z0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # If short URL, fetch redirect to get real ID
                if "v.douyin.com" in url:
                    final_url = self._resolve_short_url(url)
                    if final_url:
                        real_match = re.search(r"video/(\d+)", final_url)
                        if real_match:
                            return real_match.group(1)
                    return None  # Failed to resolve short URL
                return video_id
        return None

    def _resolve_short_url(self, url: str) -> Optional[str]:
        """Resolve short URL to get final URL"""
        try:
            resp = requests.get(url, headers=self.headers, timeout=10, allow_redirects=True)
            return resp.url
        except requests.RequestException:
            return None

    def _fetch_video_data(self, video_id: str) -> dict:
        """Fetch video data via share page or API"""
        # Method 1: Try mobile share page (iesdouyin.com) - more reliable
        result = self._fetch_from_share_page(video_id)
        if result and result.get("desc"):
            return result

        # Method 2: Try main site (often blocked by anti-scraping)
        page_url = f"https://www.douyin.com/video/{video_id}"
        try:
            resp = requests.get(page_url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            content = resp.text

            # Try to extract __INIT_DATA__
            init_match = re.search(
                r'window\.__INIT_DATA__\s*=\s*({.*?})\s*;?\s*</script>',
                content,
                re.DOTALL,
            )
            if init_match:
                try:
                    data = json.loads(init_match.group(1))
                    if "videoDetail" in data:
                        return data["videoDetail"]
                    return data
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Try RENDER_DATA
            render_match = re.search(
                r'window\.__RENDER_DATA__\s*=\s*({.*?})\s*;?\s*</script>',
                content,
                re.DOTALL,
            )
            if render_match:
                try:
                    import urllib.parse
                    decoded = urllib.parse.parse_qs(render_match.group(1))
                    return decoded
                except Exception:
                    pass

            return self._parse_html_fallback(content)

        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch 抖音 video: {e}")

    def _fetch_from_share_page(self, video_id: str) -> Optional[dict]:
        """Fetch video data from mobile share page (iesdouyin.com)"""
        share_url = f"https://www.iesdouyin.com/share/video/{video_id}/?region=CN&from=web_code_link"
        mobile_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        }

        try:
            resp = requests.get(share_url, headers=mobile_headers, timeout=15)
            if resp.status_code != 200:
                return None

            content = resp.text
            result = {}

            # Extract desc (description/caption)
            desc_match = re.search(r'"desc"\s*:\s*"([^"]+)"', content)
            if desc_match:
                result["desc"] = desc_match.group(1)

                # Extract tags from desc (format: #标签名)
                tags = re.findall(r'#([^#\s]+)', result["desc"])
                if tags:
                    result["tag_list"] = tags

            return result if result else None

        except requests.RequestException:
            return None

    def _parse_html_fallback(self, content: str) -> dict:
        """Fallback parsing from HTML"""
        result = {}

        title_match = re.search(r'<title>([^<]+)</title>', content)
        if title_match:
            result["title"] = title_match.group(1).replace("- 抖音", "").strip()

        desc_match = re.search(r'"desc"\s*:\s*"([^"]+)"', content)
        if desc_match:
            result["desc"] = desc_match.group(1)

        return result

    def _parse_metadata(self, url: str, data: dict) -> VideoMetadata:
        """Parse raw data into VideoMetadata"""
        desc = data.get("desc", "")
        # Title: use first line of desc (before \n), remove hashtags from title
        title = data.get("title", "")
        if not title and desc:
            first_line = desc.split("\\n")[0].split("\n")[0]
            # Remove trailing hashtags from title line
            title = re.sub(r'\s*#[^#]*$', '', first_line).strip()

        tags_raw = data.get("label_list", data.get("tag_list", []))
        tags = []
        for t in tags_raw:
            if isinstance(t, str):
                tags.append(t)
            elif isinstance(t, dict):
                name = t.get("name", t.get("label_name", ""))
                if name:
                    tags.append(name)

        raw_time = data.get("create_time", data.get("mtime", ""))
        if isinstance(raw_time, int):
            publish_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(raw_time))
        elif raw_time:
            publish_time = str(raw_time)
        else:
            publish_time = ""

        topic = ""
        challenge = data.get("challenge", {})
        if challenge:
            topic = challenge.get("title", "")

        return VideoMetadata(
            platform=self.PLATFORM_NAME,
            url=url,
            title=self._clean_text(title) or "无标题",
            caption=desc.replace('\\n', '\n').strip() if desc else None,
            tags=tags,
            publish_time=publish_time,
            topic=topic,
        )
