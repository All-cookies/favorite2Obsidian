"""B站 (Bilibili) parser"""
import json
import re
import time
from typing import Optional

import requests

from parsers.base import BaseParser
from parsers.data import VideoMetadata


class BilibiliParser(BaseParser):
    """Parser for B站 (Bilibili) videos"""

    PLATFORM_NAME = "B站"
    API_URL = "https://api.bilibili.com/x/web-interface/view"
    TAG_API_URL = "https://api.bilibili.com/x/tag/archive/tags"
    PLAY_URL_API = "https://api.bilibili.com/x/player/playurl"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.bilibili.com/",
        }
        self._bvid = ""
        self._cid = 0

    def detect(self, url: str) -> bool:
        patterns = [
            r"bilibili\.com/video/(BV[a-zA-Z0-9]+)",
            r"bilibili\.com/video/(av\d+)",
            r"b23\.tv/[a-zA-Z0-9]+",
        ]
        return any(re.search(p, url) for p in patterns)

    def parse(self, url: str) -> VideoMetadata:
        """Parse B站 video metadata via API"""
        bvid = self._extract_bvid(url)
        if not bvid:
            raise ValueError(f"Invalid B站 URL: {url}")
        self._bvid = bvid

        data = self._fetch_video_data(bvid)
        self._cid = data.get("cid", 0)
        # Fallback: get cid from first page
        if not self._cid:
            pages = data.get("pages", [])
            if pages:
                self._cid = pages[0].get("cid", 0)

        tags = self._fetch_tags(bvid)
        video_url = self._fetch_video_url(bvid, self._cid)
        return self._parse_metadata(url, data, tags, video_url)

    def _extract_bvid(self, url: str) -> Optional[str]:
        """Extract BV号 from URL"""
        # Direct BV pattern
        bv_match = re.search(r"bilibili\.com/video/(BV[a-zA-Z0-9]+)", url)
        if bv_match:
            return bv_match.group(1)

        # av号 pattern (convert to BV)
        av_match = re.search(r"bilibili\.com/video/(av\d+)", url)
        if av_match:
            av_id = av_match.group(1).replace("av", "")
            return self._av_to_bv(av_id)

        # Short URL pattern
        short_match = re.search(r"b23\.tv/([a-zA-Z0-9]+)", url)
        if short_match:
            resolved = self._resolve_short_url(short_match.group(1))
            if resolved:
                bv_match = re.search(r"bilibili\.com/video/(BV[a-zA-Z0-9]+)", resolved)
                if bv_match:
                    return bv_match.group(1)

        return None

    def _av_to_bv(self, av_id: str) -> str:
        """Convert AV号 to BV号 using API"""
        try:
            resp = requests.get(
                f"https://api.bilibili.com/x/web-interface/view?aid={av_id}",
                headers=self.headers,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                return data["data"]["bvid"]
        except requests.RequestException:
            pass
        return ""

    def _resolve_short_url(self, short_code: str) -> Optional[str]:
        """Resolve B站 short URL"""
        try:
            resp = requests.get(
                f"https://b23.tv/{short_code}",
                headers=self.headers,
                timeout=10,
                allow_redirects=True,
            )
            return resp.url
        except requests.RequestException:
            return None

    def _fetch_video_data(self, bvid: str) -> dict:
        """Fetch video data from Bilibili API"""
        try:
            resp = requests.get(
                f"{self.API_URL}?bvid={bvid}",
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise ValueError(f"B站 API error: {data.get('message', 'Unknown error')}")

            return data.get("data", {})

        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch B站 video: {e}")

    def _fetch_tags(self, bvid: str) -> list:
        """Fetch video tags from separate tags API"""
        try:
            resp = requests.get(
                f"{self.TAG_API_URL}?bvid={bvid}",
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0:
                return [t["tag_name"] for t in data.get("data", []) if t.get("tag_name")]

        except requests.RequestException:
            pass

        return []

    def _fetch_video_url(self, bvid: str, cid: int) -> str:
        """Fetch video/audio stream URL from Bilibili player API
        
        B站 uses DASH format (video + audio separated).
        For transcription, we only need the audio stream.
        We also try the old MP4 format as fallback.
        """
        if not cid:
            return ""

        try:
            # Try DASH format first (qn=16 = 360P for lower bandwidth)
            resp = requests.get(
                f"{self.PLAY_URL_API}",
                params={
                    "bvid": bvid,
                    "cid": cid,
                    "qn": 16,
                    "fnver": 0,
                    "fnval": 16,  # Request DASH format
                    "fourk": 0,
                },
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                # Try without DASH (old MP4 format)
                return self._fetch_video_url_mp4(bvid, cid)

            result = data.get("data", {})
            dash = result.get("dash", {})

            # Get audio stream URL (for transcription)
            audio_list = dash.get("audio", [])
            if audio_list:
                # Pick the lowest quality audio (smallest file)
                audio_list.sort(key=lambda x: x.get("bandwidth", 0))
                audio_url = audio_list[0].get("baseUrl", "") or audio_list[0].get("base_url", "")
                if audio_url:
                    return audio_url

            # Get video stream URL as fallback
            video_list = dash.get("video", [])
            if video_list:
                video_url = video_list[0].get("baseUrl", "") or video_list[0].get("base_url", "")
                if video_url:
                    return video_url

            # Fallback to old format
            return self._fetch_video_url_mp4(bvid, cid)

        except requests.RequestException as e:
            print(f"[!] Failed to fetch video URL: {e}")
            return ""

    def _fetch_video_url_mp4(self, bvid: str, cid: int) -> str:
        """Fetch video URL in old MP4 format (non-DASH)"""
        try:
            resp = requests.get(
                f"{self.PLAY_URL_API}",
                params={
                    "bvid": bvid,
                    "cid": cid,
                    "qn": 16,
                    "fnver": 0,
                    "fnval": 0,  # No DASH
                    "fourk": 0,
                },
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0:
                durl = data.get("data", {}).get("durl", [])
                if durl:
                    return durl[0].get("url", "")
        except requests.RequestException:
            pass
        return ""

    def _parse_metadata(self, url: str, data: dict, tags: list = None, video_url: str = "") -> VideoMetadata:
        """Parse API response into VideoMetadata"""
        title = data.get("title", "")
        desc = data.get("desc", "")
        owner = data.get("owner", {})
        stat = data.get("stat", {})

        # UP 主
        author = owner.get("name", "")

        # 视频时长（秒）
        duration = data.get("duration", 0)

        # 播放统计
        stats = {}
        if stat.get("view"):
            stats["播放"] = stat["view"]
        if stat.get("danmaku"):
            stats["弹幕"] = stat["danmaku"]
        if stat.get("like"):
            stats["点赞"] = stat["like"]
        if stat.get("coin"):
            stats["投币"] = stat["coin"]
        if stat.get("favorite"):
            stats["收藏"] = stat["favorite"]
        if stat.get("share"):
            stats["分享"] = stat["share"]
        if stat.get("reply"):
            stats["评论"] = stat["reply"]

        # Use tags from tags API if available
        if tags is None:
            tags = []

        # Fallback: try tags from main API response (older format)
        if not tags:
            tag_list = data.get("tags", [])
            for tag in tag_list:
                if isinstance(tag, dict):
                    tag_name = tag.get("tag_name", "")
                    if tag_name:
                        tags.append(tag_name)

        # Extract topic (category) - try tname_v2 first, then tname
        topic = data.get("tname_v2", "") or data.get("tname", "")

        # Parse publish time
        raw_time = data.get("pubdate", 0)
        if isinstance(raw_time, int) and raw_time > 0:
            publish_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(raw_time))
        else:
            publish_time = ""

        return VideoMetadata(
            platform=self.PLATFORM_NAME,
            url=url,
            title=self._clean_text(title),
            caption=self._clean_text(desc),
            tags=tags,
            publish_time=publish_time,
            topic=topic,
            author=author,
            duration=duration,
            stats=stats,
            video_url=video_url,
        )
