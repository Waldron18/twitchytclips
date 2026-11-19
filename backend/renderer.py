"""
renderer.py - OpenCV facecam detection, 9:16 vertical split-screen canvas creation,
animated .ass karaoke subtitle generation, and hardware-accelerated FFmpeg video rendering.
"""
import os
import cv2
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from backend.config import TARGET_WIDTH, TARGET_HEIGHT, EXPORTS_DIR
from backend.hardware_profiler import detect_hardware_profile

logger = logging.getLogger("clipforge.renderer")

def detect_facecam_box(video_path: str, sample_count: int = 4) -> Optional[Dict[str, float]]:
    """
    Fast corner motion/variance analysis across 4 sampled video frames.
    Resizes frames to 320x180 for sub-50ms execution.
    """
    if not os.path.exists(video_path):
        return {"x": 0.03, "y": 0.05, "w": 0.35, "h": 0.35}

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"x": 0.03, "y": 0.05, "w": 0.35, "h": 0.35}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if total_frames <= 0 or width <= 0 or height <= 0:
            cap.release()
            return {"x": 0.03, "y": 0.05, "w": 0.35, "h": 0.35}

        frame_indices = [int(i * total_frames / max(sample_count, 1)) for i in range(sample_count)]
        prev_small = None
        corner_motion = {"top_left": 0.0, "top_right": 0.0, "bottom_left": 0.0, "bottom_right": 0.0}

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # Downsample for blazing fast variance computation
            small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_NEAREST)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            if prev_small is not None:
                diff = cv2.absdiff(gray, prev_small)
                # 320x180: h_split=72, w_split=128
                corner_motion["top_left"] += float(diff[0:72, 0:128].mean())
                corner_motion["top_right"] += float(diff[0:72, 192:320].mean())
                corner_motion["bottom_left"] += float(diff[108:180, 0:128].mean())
                corner_motion["bottom_right"] += float(diff[108:180, 192:320].mean())

            prev_small = gray

        cap.release()

        # Select highest motion/variance corner
        best_corner = max(corner_motion, key=corner_motion.get)
        if best_corner == "top_right":
            return {"x": 0.62, "y": 0.05, "w": 0.35, "h": 0.35}
        elif best_corner == "bottom_left":
            return {"x": 0.03, "y": 0.60, "w": 0.35, "h": 0.35}
        elif best_corner == "bottom_right":
            return {"x": 0.62, "y": 0.60, "w": 0.35, "h": 0.35}
        else:
            return {"x": 0.03, "y": 0.05, "w": 0.35, "h": 0.35}

    except Exception as e:
        logger.warning(f"Facecam detection heuristic error: {e}")
        return {"x": 0.03, "y": 0.05, "w": 0.35, "h": 0.35}


def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_karaoke_ass_file(
    words: List[Dict[str, Any]],
    output_ass_path: str,
    clip_start_offset: float = 0.0,
    style: str = "karaoke_yellow"
) -> str:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file.
    Renders 2-4 words per line with dynamic active-word highlighting.
    """
    output_ass_path = str(Path(output_ass_path).resolve())

    # Style colors (ASS format is &HAABBGGRR)
    # Yellow highlight: &H0000FFFF (BGR)
    # Neon Green: &H0000FF00
    # Clean White: &H00FFFFFF
    if style == "neon_green":
        highlight_color = "&H0000FF00"
    elif style == "clean_white":
        highlight_color = "&H00DDEEFF"
    else:  # default karaoke_yellow
        highlight_color = "&H0000FFFF"

    header = f"""[Script Info]
Title: ClipForge Animated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,54,&H00FFFFFF,{highlight_color},&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.5,2,40,40,280,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # Group words into 3-word chunks
    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        if not chunk:
            continue

        line_start = max(0.0, chunk[0]["start"] - clip_start_offset)
        line_end = max(line_start + 0.3, chunk[-1]["end"] - clip_start_offset)

        # For each word in the chunk, create a subtitle event where that word is highlighted
        for active_idx, w in enumerate(chunk):
            w_start = max(0.0, w["start"] - clip_start_offset)
            w_end = max(w_start + 0.15, w["end"] - clip_start_offset)

            line_text_parts = []
            for idx, cw in enumerate(chunk):
                word_clean = cw["word"].upper()
                if idx == active_idx:
                    # Highlighted active word with color change & subtle bounce
                    line_text_parts.append(f"{{\\c{highlight_color}\\fscx110\\fscy110}}{word_clean}{{\\r}}")
                else:
                    line_text_parts.append(f"{{\\c&H00FFFFFF}}{word_clean}")

            display_line = " ".join(line_text_parts)
            events.append(
                f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{display_line}"
            )

    content = header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_ass_path


def render_vertical_clip(
    video_segment_path: str,
    mastered_audio_path: str,
    output_mp4_path: str,
    facecam_rect: Optional[Dict[str, float]] = None,
    has_facecam: bool = True,
    words: Optional[List[Dict[str, Any]]] = None,
    clip_start_offset: float = 0.0,
    subtitle_style: str = "karaoke_yellow",
    progress_cb: Optional[Any] = None
) -> str:
    """
    Renders 9:16 vertical short-form video (1080x1920) with:
    - Top 35% facecam / Bottom 65% gameplay split screen (or blur fallback)
    - Burned-in animated karaoke subtitles
    - Hardware-accelerated encoding (NVENC or libx264)
    """
    video_segment_path = str(Path(video_segment_path).resolve())
    mastered_audio_path = str(Path(mastered_audio_path).resolve())
    output_mp4_path = str(Path(output_mp4_path).resolve())
    temp_dir = Path(output_mp4_path).parent

    profile = detect_hardware_profile()

    # Step 1: Subtitles ASS generation
    ass_path = None
    if words:
        ass_path = str(temp_dir / "subtitles.ass")
        generate_karaoke_ass_file(words, ass_path, clip_start_offset, style=subtitle_style)

    # Step 2: Build FFmpeg video filtergraph
    # Target canvas: 1080 x 1920
    # Top 35%: 1080 x 672 (Facecam)
    # Bottom 65%: 1080 x 1248 (Gameplay)
    if has_facecam and facecam_rect:
        fx = facecam_rect.get("x", 0.05)
        fy = facecam_rect.get("y", 0.05)
        fw = facecam_rect.get("w", 0.35)
        fh = facecam_rect.get("h", 0.35)

        # Expressions for crop filter in ffmpeg
        crop_face = f"crop=w=iw*{fw}:h=ih*{fh}:x=iw*{fx}:y=ih*{fy},scale=1080:672:force_original_aspect_ratio=increase,crop=1080:672"
        crop_game = f"crop=w=ih*(1080/1248):h=ih:x=(iw-ih*(1080/1248))/2:y=0,scale=1080:1248"
        base_filter = f"[0:v]split=2[cam_in][game_in];[cam_in]{crop_face}[top];[game_in]{crop_game}[bottom];[top][bottom]vstack=inputs=2[stacked]"
        last_out = "[stacked]"
    else:
        # Blur background fallback (no facecam)
        base_filter = (
            f"[0:v]split=2[blur_in][main_in];"
            f"[blur_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:24[bg];"
            f"[main_in]scale=1080:-1[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[stacked]"
        )
        last_out = "[stacked]"

    # If subtitles present, add ass filter
    if ass_path and os.path.exists(ass_path):
        # Escape path for FFmpeg filter on Windows
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
        full_filter = f"{base_filter};{last_out}ass='{escaped_ass}'[v_out]"
        map_v = "[v_out]"
    else:
        full_filter = base_filter
        map_v = last_out

    # Step 3: FFmpeg command construction
    cmd = [
        "ffmpeg", "-y",
        "-threads", "0",
        "-i", video_segment_path,
        "-i", mastered_audio_path,
        "-filter_complex", full_filter,
        "-map", map_v,
        "-map", "1:a",
        "-c:v", profile.ffmpeg_video_encoder,
        *profile.ffmpeg_encoder_params,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_mp4_path
    ]

    logger.info(f"Rendering vertical clip with {profile.ffmpeg_video_encoder} to {output_mp4_path}...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.warning(f"Hardware encode failed ({proc.stderr}). Retrying with libx264 ultrafast fallback...")
        # Fallback to libx264 software encoder
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", video_segment_path,
            "-i", mastered_audio_path,
            "-filter_complex", full_filter,
            "-map", map_v,
            "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_mp4_path
        ]
        subprocess.run(cmd_fallback, check=True)

    logger.info(f"Vertical video successfully rendered: {output_mp4_path}")
    return output_mp4_path
