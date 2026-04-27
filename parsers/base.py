"""Base parser class for video platforms"""
import re
from abc import ABC, abstractmethod
from typing import Optional

from parsers.data import VideoMetadata


class BaseParser(ABC):
    """Abstract base class for platform-specific parsers"""

    @abstractmethod
    def detect(self, url: str) -> bool:
        """Check if URL matches this platform"""
        pass

    @abstractmethod
    def parse(self, url: str) -> VideoMetadata:
        """Parse video metadata from URL"""
        pass

    def extract_video_id(self, url: str, pattern: str) -> Optional[str]:
        """Extract video ID from URL using regex pattern"""
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace"""
        if not text:
            return ""
        return " ".join(text.split())
