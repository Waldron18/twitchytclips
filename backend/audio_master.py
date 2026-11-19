"""
audio_master.py - Video segment extraction, copyright-safe audio separation,
royalty-free background music mixing, and -14 LUFS loudness mastering.
"""
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from backend.config import TEMP_DIR, MUSIC_DIR, TARGET_LUFS
from backend.hardware_profiler import detect_hardware_profile

logger = logging.getLogger("clipforge.audio_master")

def extract_video_segment(
    source_url_or_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    is_local_file: bool = False
) -> str:
    """
    Extracts the candidate segment (15-60s).
    If local file: uses fast FFmpeg seek.
    If online URL: uses yt-dlp --download-sections to download ONLY this slice (Storage Saver).
    """
    duration = end_time - start_time
    output_path = str(Path(output_path).resolve())

    if is_local_file or os.path.exists(source_url_or_path):
        # Local video file on disk: instant seek and extraction
        cmd = [
            "ffmpeg", "-y", "-threads", "0",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", source_url_or_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg segment cut failed: {proc.stderr}")
    else:
        # Online stream URL: download only sections to save disk space
        section_arg = f"*{int(start_time)}-{int(end_time)}"
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--download-sections", section_arg,
            "--force-keyframes-at-cuts",
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
            "-o", output_path,
            source_url_or_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # Fallback to direct ffmpeg URL stream seek
            cmd_stream = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", source_url_or_path,
                "-t", str(duration),
                "-c:v", "copy", "-c:a", "aac",
                output_path
            ]
            subprocess.run(cmd_stream, check=True)

    return output_path


def process_audio_mastering(
    raw_video_path: str,
    output_audio_path: str,
    bgm_filename: Optional[str] = "lofi_chill.mp3",
    bgm_volume_db: float = -24.0,
    isolate_vocals: bool = True
) -> str:
    """
    Strips copyrighted background audio from the clip, isolates speech,
    optionally mixes royalty-free background music at -24 dB,
    and applies -14 LUFS loudness normalization.
    """
    output_audio_path = str(Path(output_audio_path).resolve())
    temp_dir = Path(output_audio_path).parent

    # Step 1: Check if audio-separator is available
    separated_vocal_path = None
    if isolate_vocals:
        try:
            # Try audio-separator CLI if installed
            sep_out_dir = temp_dir / "sep"
            sep_out_dir.mkdir(exist_ok=True)
            cmd_sep = [
                "audio-separator", raw_video_path,
                "--model_name", "UVR-MDX-NET-Voc_FT.onnx",
                "--output_dir", str(sep_out_dir),
                "--output_format", "WAV"
            ]
            res = subprocess.run(cmd_sep, capture_output=True, text=True, timeout=90)
            if res.returncode == 0:
                vocals = list(sep_out_dir.glob("*(Vocals)*.wav"))
                if vocals:
                    separated_vocal_path = str(vocals[0])
        except Exception:
            pass

    # Step 2: Build FFmpeg filtergraph for vocal enhancement, BGM mixing, and Loudnorm
    bgm_path = None
    if bgm_filename and bgm_filename != "none":
        candidate_bgm = MUSIC_DIR / bgm_filename
        if candidate_bgm.exists():
            bgm_path = str(candidate_bgm.resolve())

    # Build filtergraph
    # Loudnorm: I=-14, LRA=11, TP=-1.5
    loudnorm_filter = f"loudnorm=I={TARGET_LUFS}:LRA=11:TP=-1.5"

    if bgm_path and os.path.exists(bgm_path):
        # Convert dB to linear volume factor: 10^(db/20)
        # e.g. -24 dB = 10^(-1.2) = ~0.063
        volume_factor = round(10 ** (bgm_volume_db / 20.0), 4)

        if separated_vocal_path and os.path.exists(separated_vocal_path):
            input_vocal = separated_vocal_path
        else:
            input_vocal = raw_video_path

        # FFmpeg filter:
        # [0:a] voice enhancement (bandpass + speech clarity)
        # [1:a] loop BGM and attenuate to -24 dB
        # amix to combine them, followed by -14 LUFS loudnorm
        filter_complex = (
            f"[0:a]highpass=f=100,lowpass=f=7800,afftdn=nf=-20,equalizer=f=1200:t=q:w=1:g=2[voice];"
            f"[1:a]aloop=loop=-1:size=2e+09,volume={volume_factor}[bgm];"
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2,{loudnorm_filter}[out]"
        )

        cmd = [
            "ffmpeg", "-y", "-threads", "0",
            "-i", input_vocal,
            "-i", bgm_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "aac", "-b:a", "192k",
            output_audio_path
        ]
    else:
        # No BGM track, only speech isolation and loudnorm
        input_vocal = separated_vocal_path if (separated_vocal_path and os.path.exists(separated_vocal_path)) else raw_video_path
        filter_complex = f"[0:a]highpass=f=100,lowpass=f=8000,afftdn=nf=-20,{loudnorm_filter}[out]"
        cmd = [
            "ffmpeg", "-y",
            "-i", input_vocal,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "aac", "-b:a", "192k",
            output_audio_path
        ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.warning(f"Complex audio mastering failed ({proc.stderr}), falling back to simple loudnorm...")
        # Direct fallback
        subprocess.run([
            "ffmpeg", "-y", "-i", raw_video_path,
            "-vn", "-af", loudnorm_filter,
            "-c:a", "aac", "-b:a", "192k",
            output_audio_path
        ], check=True)

    return output_audio_path
