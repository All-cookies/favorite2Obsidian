"""Video transcription using faster-whisper with hf-mirror"""
import os
import subprocess
import tempfile
from typing import Optional


def download_audio(video_url: str, output_path: str, cookies: str = "", referer: str = "") -> bool:
    """Download video and extract audio using ffmpeg
    
    Args:
        video_url: Video stream URL
        output_path: Path to save audio (WAV format)
        cookies: Optional cookie string for authentication
        referer: Optional referer header (needed for B站)
        
    Returns:
        True if successful
    """
    cmd = [
        "ffmpeg",
        "-i", video_url,
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",  # Mono
        "-y",  # Overwrite
        output_path,
        "-loglevel", "error"
    ]
    
    env = os.environ.copy()
    
    # Build headers for ffmpeg
    headers_parts = []
    if cookies:
        headers_parts.append(f"Cookie: {cookies}")
    if referer:
        headers_parts.append(f"Referer: {referer}")
    
    # B站 specifically requires User-Agent
    if "bilivideo.com" in video_url or "bilivideo" in video_url:
        headers_parts.append("User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    if headers_parts:
        cmd.insert(1, "-headers")
        cmd.insert(2, "\r\n".join(headers_parts))
    
    try:
        result = subprocess.run(cmd, env=env, timeout=300, capture_output=True)
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr.decode()}")
            return False
        return os.path.exists(output_path)
    except subprocess.TimeoutExpired:
        print("ffmpeg timeout (5 min)")
        return False
    except Exception as e:
        print(f"ffmpeg error: {e}")
        return False


def transcribe_audio(audio_path: str, language: str = "zh") -> str:
    """Transcribe audio using faster-whisper
    
    Args:
        audio_path: Path to audio file (WAV format preferred)
        language: Language code (default: zh for Chinese)
        
    Returns:
        Transcription text
    """
    # Set HF mirror for Chinese users
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper not installed. Install with:\n"
            "pip3 install faster-whisper"
        )
    
    # Load model (tiny for speed, can use small/medium for better quality)
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    # Transcribe
    segments, info = model.transcribe(audio_path, language=language)
    
    # Combine segments
    text = "".join([s.text for s in segments])
    
    return text.strip()


def transcribe_video(video_url: str, cookies: str = "", language: str = "zh", referer: str = "") -> str:
    """Download video and transcribe audio
    
    Args:
        video_url: Video stream URL
        cookies: Optional cookie string for authentication
        language: Language code (default: zh)
        referer: Optional referer header (needed for B站)
        
    Returns:
        Transcription text
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.wav")
        
        # Download and extract audio
        print(f"[transcribe] Downloading audio from video...")
        if not download_audio(video_url, audio_path, cookies=cookies, referer=referer):
            raise RuntimeError("Failed to download/extract audio from video")
        
        # Check audio file
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            raise RuntimeError("Audio file too small or missing")
        
        # Transcribe
        print(f"[transcribe] Transcribing audio...")
        text = transcribe_audio(audio_path, language)
        
        return text
