"""Video metadata dataclass"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VideoMetadata:
    platform: str
    url: str
    title: str
    caption: str = ""
    tags: List[str] = field(default_factory=list)
    publish_time: str = ""
    topic: str = ""
    author: str = ""
    duration: int = 0  # 视频时长（秒）
    stats: Dict = field(default_factory=dict)  # 播放/点赞/投币等
    video_url: str = ""  # 视频流直链
    transcription: str = ""  # 视频转写文本

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "url": self.url,
            "title": self.title,
            "caption": self.caption,
            "tags": self.tags,
            "publish_time": self.publish_time,
            "topic": self.topic,
            "author": self.author,
            "duration": self.duration,
            "stats": self.stats,
            "video_url": self.video_url,
            "transcription": self.transcription,
        }
