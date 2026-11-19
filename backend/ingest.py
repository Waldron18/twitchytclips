"""
ingest.py - Unified media ingestion for YouTube, Twitch, Kick, and local files.
Supports audio-first extraction (Storage Saver Mode) and chat logs.
"""
import os
import json
import re
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from backend.config import TEMP_DIR
from backend.hardware_profiler import detect_hardware_profile

logger = logging.getLogger("clipforge.ingest")

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def detect_platform(url_or_path: str) -> str:
    lower = url_or_path.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    elif "twitch.tv" in lower:
        return "twitch"
    elif "kick.com" in lower:
        return "kick"
    elif os.path.exists(url_or_path):
        return "local"
    return "web"

def probe_file_info(file_path: str) -> Dict[str, Any]:
    """Uses ffprobe to extract duration, width, height, fps, and audio tracks."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
        "-of", "json", file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        width, height, fps = 1920, 1080, 30.0

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width", 1920))
                height = int(stream.get("height", 1080))
                fps_str = stream.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = round(float(num) / max(float(den), 1.0), 2)
                else:
                    fps = float(fps_str)
                break
        return {"duration": duration, "width": width, "height": height, "fps": fps}
    except Exception as e:
        logger.warning(f"ffprobe failed on {file_path}: {e}")
        return {"duration": 0.0, "width": 1920, "height": 1080, "fps": 30.0}


async def ingest_media(
    source_url_or_path: str,
    project_id: str,
    storage_saver_override: Optional[bool] = None,
    live_capture_seconds: int = 600,
    progress_cb: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Downloads or extracts audio (and video if storage saver is off).
    Supports:
    - Pre-recorded YouTube / Twitch / Kick VODs
    - Active live streams on Twitch / YouTube / Kick (captures a rolling window of N seconds)
    - Local video files (.mp4, .mkv, .mov)
    """
    project_dir = TEMP_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    platform = detect_platform(source_url_or_path)
    profile = detect_hardware_profile()
    storage_saver = profile.storage_saver_mode if storage_saver_override is None else storage_saver_override

    if progress_cb:
        await progress_cb(5.0, f"Analyzing {platform} source...")

    audio_path = str(project_dir / "audio.m4a")
    video_path: Optional[str] = None
    chat_path: Optional[str] = None
    title = "Video Project"
    duration = 0.0
    is_live_stream = False

    if platform == "local":
        local_path = os.path.abspath(source_url_or_path)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        title = Path(local_path).stem
        info = probe_file_info(local_path)
        duration = info["duration"]

        if progress_cb:
            await progress_cb(15.0, "Extracting audio track with FFmpeg...")

        cmd = [
            "ffmpeg", "-y", "-i", local_path,
            "-vn", "-c:a", "aac", "-b:a", "192k",
            audio_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {proc.stderr}")

        video_path = local_path

    else:
        # Online stream or video (YouTube, Twitch, Kick)
        if progress_cb:
            await progress_cb(10.0, "Inspecting stream metadata via yt-dlp...")

        # Step 1: Probe metadata & check if stream is currently live
        cmd_info = ["python", "-m", "yt_dlp", "--dump-json", "--no-warnings", source_url_or_path]
        try:
            res = subprocess.run(cmd_info, capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                meta = json.loads(res.stdout)
                title = meta.get("title", f"{platform.title()} Video")
                duration = float(meta.get("duration", 0.0) or 0.0)
                is_live_stream = bool(meta.get("is_live", False) or meta.get("live_status") == "is_live")
        except Exception as e:
            logger.warning(f"Metadata dump failed, continuing: {e}")

        # Step 2: Handle Live Streams vs VODs
        if is_live_stream or duration <= 0.0:
            # Active Live Stream: capture a rolling window of `live_capture_seconds`
            capture_dur = max(60, min(live_capture_seconds, 3600))
            duration = float(capture_dur)
            title = f"[LIVE] {title}"

            if progress_cb:
                await progress_cb(20.0, f"Recording live stream window ({int(capture_dur // 60)} minutes)...")

            # Resolve direct HLS stream URL using yt-dlp -g
            cmd_get_url = ["python", "-m", "yt_dlp", "-g", source_url_or_path]
            proc_url = subprocess.run(cmd_get_url, capture_output=True, text=True, timeout=20)
            if proc_url.returncode != 0 or not proc_url.stdout.strip():
                raise RuntimeError(f"Could not connect to live stream: {proc_url.stderr.strip() or 'Channel may be offline'}")

            stream_urls = proc_url.stdout.strip().splitlines()
            live_stream_url = stream_urls[0]

            # In Storage Saver mode, capture audio stream directly with FFmpeg -t
            if storage_saver:
                cmd_rec = [
                    "ffmpeg", "-y",
                    "-i", live_stream_url,
                    "-t", str(capture_dur),
                    "-vn", "-c:a", "aac", "-b:a", "192k",
                    audio_path
                ]
                subprocess.run(cmd_rec, check=True, timeout=capture_dur + 30)
            else:
                # Capture both video and audio
                v_out = str(project_dir / "live_video.mp4")
                cmd_rec = [
                    "ffmpeg", "-y",
                    "-i", live_stream_url,
                    "-t", str(capture_dur),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    v_out
                ]
                subprocess.run(cmd_rec, check=True, timeout=capture_dur + 30)
                video_path = v_out
                # Extract audio
                subprocess.run(["ffmpeg", "-y", "-i", v_out, "-vn", "-c:a", "aac", audio_path], check=True)

        else:
            # Standard VOD / Pre-recorded stream
            if progress_cb:
                await progress_cb(20.0, "Downloading audio-only stream (Storage Saver)...")

            ytdlp_audio_out = str(project_dir / "audio.%(ext)s")
            cmd_audio = [
                "python", "-m", "yt_dlp",
                "-x",
                "--audio-format", "m4a",
                "--no-playlist",
                "-o", ytdlp_audio_out,
                source_url_or_path
            ]
            proc_audio = subprocess.run(cmd_audio, capture_output=True, text=True)
            if proc_audio.returncode != 0:
                # Fallback to general bestaudio
                cmd_audio_fallback = [
                    "python", "-m", "yt_dlp",
                    "-f", "ba/b",
                    "-o", str(project_dir / "raw_audio.%(ext)s"),
                    source_url_or_path
                ]
                subprocess.run(cmd_audio_fallback, check=True)
                raw_files = list(project_dir.glob("raw_audio.*"))
                if raw_files:
                    subprocess.run(["ffmpeg", "-y", "-i", str(raw_files[0]), "-vn", "-c:a", "aac", audio_path], check=True)
            else:
                found = list(project_dir.glob("audio.*"))
                if found:
                    audio_path = str(found[0])

            # Chat replay / comments if available
            try:
                cmd_chat = [
                    "python", "-m", "yt_dlp",
                    "--skip-download",
                    "--write-comments",
                    "--write-subs",
                    "-o", str(project_dir / "comments"),
                    source_url_or_path
                ]
                subprocess.run(cmd_chat, capture_output=True, text=True, timeout=15)
                possible_chats = list(project_dir.glob("comments*.info.json")) + list(project_dir.glob("comments*.json"))
                if possible_chats:
                    chat_path = str(possible_chats[0])
            except Exception:
                pass

            if not storage_saver:
                if progress_cb:
                    await progress_cb(40.0, "Downloading full high-res video...")
                v_out = str(project_dir / "full_video.%(ext)s")
                cmd_video = [
                    "python", "-m", "yt_dlp",
                    "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
                    "--no-playlist",
                    "-o", v_out,
                    source_url_or_path
                ]
                subprocess.run(cmd_video, check=True)
                v_files = list(project_dir.glob("full_video.*"))
                if v_files:
                    video_path = str(v_files[0])

    if duration <= 0.0 and os.path.exists(audio_path):
        duration = probe_file_info(audio_path)["duration"]

    if progress_cb:
        await progress_cb(50.0, f"Ingestion complete: '{title}' ({round(duration, 1)}s)")

    return {
        "title": title,
        "platform": platform,
        "duration": duration,
        "audio_path": audio_path,
        "video_path": video_path,
        "chat_path": chat_path,
        "storage_saver": storage_saver,
        "is_live_stream": is_live_stream
    }
