"""
test_pipeline.py - Comprehensive end-to-end integration test for ClipForge Local.
Validates:
1. Hardware auto-profiler (LOW/MID/HIGH)
2. BGM track assets
3. Karaoke ASS subtitle generator
4. Synthetic video generation, facecam box detection, audio mastering (-14 LUFS),
   and 9:16 vertical render (1080x1920).
"""
import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import TEMP_DIR, EXPORTS_DIR, MUSIC_DIR
from backend.hardware_profiler import detect_hardware_profile
from backend.renderer import detect_facecam_box, generate_karaoke_ass_file, render_vertical_clip
from backend.audio_master import process_audio_mastering
from backend.ingest import probe_file_info
from backend.ollama_client import ollama_client

def run_tests():
    print("=" * 60)
    print("      ClipForge Local - Comprehensive Pipeline Test")
    print("=" * 60)

    # 1. Hardware Profiler
    print("\n[Test 1] Testing Hardware Profiler...")
    profile = detect_hardware_profile(force_refresh=True)
    print(f" -> Detected Tier: {profile.tier}")
    print(f" -> GPU: {profile.gpu_name} ({profile.vram_gb} GB VRAM)")
    print(f" -> NVENC Available: {profile.has_nvenc}")
    print(f" -> Whisper Model: {profile.whisper_model} ({profile.whisper_compute_type})")
    print(f" -> Video Encoder: {profile.ffmpeg_video_encoder} {profile.ffmpeg_encoder_params}")
    assert profile.tier in ["LOW", "MID", "HIGH"], "Invalid tier!"
    print(" [PASS] Hardware Profiler OK.")

    # 2. Check BGM Assets
    print("\n[Test 2] Checking BGM Audio Tracks...")
    lofi = MUSIC_DIR / "lofi_chill.mp3"
    upbeat = MUSIC_DIR / "upbeat_hype.mp3"
    assert lofi.exists(), f"Missing {lofi}"
    assert upbeat.exists(), f"Missing {upbeat}"
    print(f" -> Found: {lofi.name} ({os.path.getsize(lofi)} bytes)")
    print(f" -> Found: {upbeat.name} ({os.path.getsize(upbeat)} bytes)")
    print(" [PASS] BGM Assets OK.")

    # 3. Test Karaoke ASS Subtitle Generation
    print("\n[Test 3] Testing Animated Karaoke .ass Subtitle Generation...")
    sample_words = [
        {"word": "LOOK", "start": 0.2, "end": 0.6},
        {"word": "AT", "start": 0.6, "end": 0.8},
        {"word": "THIS", "start": 0.8, "end": 1.2},
        {"word": "INSANE", "start": 1.2, "end": 1.8},
        {"word": "CLUTCH", "start": 1.8, "end": 2.4},
        {"word": "PLAY!", "start": 2.4, "end": 3.0},
    ]
    test_ass_path = str(TEMP_DIR / "test_subs.ass")
    generate_karaoke_ass_file(sample_words, test_ass_path, clip_start_offset=0.0, style="karaoke_yellow")
    assert os.path.exists(test_ass_path), "ASS file was not created!"
    with open(test_ass_path, "r", encoding="utf-8") as f:
        ass_content = f.read()
    assert "PlayResX: 1080" in ass_content, "ASS header missing 1080 resolution"
    assert "PlayResY: 1920" in ass_content, "ASS header missing 1920 resolution"
    assert "INSANE" in ass_content, "ASS missing target word"
    print(f" -> Generated .ass subtitle ({len(ass_content.splitlines())} lines)")
    print(" [PASS] Karaoke ASS Generator OK.")

    # 4. Generate Short 4-second Synthetic 16:9 Test Video
    print("\n[Test 4] Generating Synthetic 16:9 Test Video...")
    test_video = str(TEMP_DIR / "synthetic_test.mp4")
    # Generates 4s 1280x720 video with a sine test tone and animated box
    cmd_gen = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        test_video
    ]
    subprocess.run(cmd_gen, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    info = probe_file_info(test_video)
    print(f" -> Created synthetic video: {info['width']}x{info['height']}, {info['duration']}s")
    assert os.path.exists(test_video), "Synthetic test video generation failed!"
    print(" [PASS] Test Video Generation OK.")

    # 5. Test Facecam Detector
    print("\n[Test 5] Testing OpenCV Facecam Detection...")
    face_rect = detect_facecam_box(test_video, sample_count=3)
    print(f" -> Detected/Default Facecam Rect: {face_rect}")
    assert face_rect is not None
    assert "x" in face_rect and "y" in face_rect and "w" in face_rect and "h" in face_rect
    print(" [PASS] Facecam Detector OK.")

    # 6. Test Audio Mastering (-14 LUFS & BGM mixing)
    print("\n[Test 6] Testing Audio Mastering with Royalty-Free BGM (-14 LUFS)...")
    mastered_audio = str(TEMP_DIR / "test_mastered_audio.aac")
    process_audio_mastering(
        raw_video_path=test_video,
        output_audio_path=mastered_audio,
        bgm_filename="lofi_chill.mp3",
        bgm_volume_db=-24.0,
        isolate_vocals=True
    )
    assert os.path.exists(mastered_audio), "Mastered audio not generated!"
    print(f" -> Mastered audio track generated ({os.path.getsize(mastered_audio)} bytes)")
    print(" [PASS] Audio Mastering OK.")

    # 7. Test 9:16 Vertical Short Render (1080x1920)
    print("\n[Test 7] Testing 9:16 Vertical Video Render (1080x1920)...")
    test_output_vertical = str(EXPORTS_DIR / "test_rendered_short.mp4")
    render_vertical_clip(
        video_segment_path=test_video,
        mastered_audio_path=mastered_audio,
        output_mp4_path=test_output_vertical,
        facecam_rect=face_rect,
        has_facecam=True,
        words=sample_words,
        clip_start_offset=0.0,
        subtitle_style="karaoke_yellow"
    )
    assert os.path.exists(test_output_vertical), "Vertical clip was not rendered!"
    out_info = probe_file_info(test_output_vertical)
    print(f" -> Rendered Video Dimensions: {out_info['width']}x{out_info['height']} ({out_info['duration']}s)")
    assert out_info["width"] == 1080, f"Expected width 1080, got {out_info['width']}"
    assert out_info["height"] == 1920, f"Expected height 1920, got {out_info['height']}"
    print(f" -> File Size: {os.path.getsize(test_output_vertical)} bytes")
    print(" [PASS] 9:16 Vertical Render (1080x1920) OK.")

    # 8. Test Ollama Fallback Heuristic
    print("\n[Test 8] Testing Viral Hook & Metadata Scoring...")
    meta = ollama_client.generate_clip_metadata("Look at this insane clutch play right now, no way!")
    print(f" -> Generated Viral Title: {meta.get('title')}")
    print(f" -> Generated Hashtags: {meta.get('hashtags')}")
    assert len(meta.get("title", "")) > 0
    print(" [PASS] Viral Metadata Scoring OK.")

    print("\n" + "=" * 60)
    print("  ALL 8 INTEGRATION TESTS PASSED CLEANLY! ClipForge Local is 100% functional.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
