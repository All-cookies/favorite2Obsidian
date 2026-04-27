"""Parser module for video platforms"""
from parsers.base import BaseParser
from parsers.data import VideoMetadata
from parsers.xhs_parser import XiaohongshuParser
from parsers.dy_parser import DouyinParser
from parsers.bilibili_parser import BilibiliParser

__all__ = [
    "BaseParser",
    "VideoMetadata",
    "XiaohongshuParser",
    "DouyinParser",
    "BilibiliParser",
]
