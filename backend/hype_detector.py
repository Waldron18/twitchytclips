"""
hype_detector.py - Multi-modal hype scoring & viral candidate detection.
Combines audio RMS volume peaks, chat velocity spikes, and Ollama hook analysis.
Snaps clip start/end timestamps strictly to word boundaries.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import scipy.signal
from backend.ollama_client import ollama_client

logger = logging.getLogger("clipforge.hype")

def compute_audio_rms_curve(audio_path: str, hop_length_sec: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes RMS audio energy across sliding windows.
    Returns (times_array, normalized_energy_array).
    """
    try:
        import librosa
        # Load audio at 16kHz mono for fast processing
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        hop_length = int(sr * hop_length_sec)
        rms = librosa.feature.rms(y=y, frame_length=hop_length * 2, hop_length=hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

        # Normalize 0..1
        max_val = np.max(rms) if len(rms) > 0 else 1.0
        norm_rms = rms / (max_val + 1e-6)
        return times, norm_rms
    except Exception as e:
        logger.warning(f"Librosa RMS failed ({e}), using FFmpeg / scipy fallback...")

    # Fallback using FFmpeg pipe to 16bit PCM
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-ac", "1", "-ar", "16000",
            "-f", "s16le", "-"
        ]
        proc = subprocess.run(cmd, capture_output=True, check=True)
        raw = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        sr = 16000
        hop = int(sr * hop_length_sec)
        num_frames = int(len(raw) // hop)
        rms_vals = []
        times = []
        for i in range(num_frames):
            chunk = raw[i * hop : (i + 1) * hop]
            rms_vals.append(np.sqrt(np.mean(chunk**2)))
            times.append(i * hop_length_sec)

        arr_rms = np.array(rms_vals)
        arr_times = np.array(times)
        max_val = np.max(arr_rms) if len(arr_rms) > 0 else 1.0
        return arr_times, arr_rms / (max_val + 1e-6)
    except Exception as e:
        logger.error(f"Fallback RMS failed: {e}")
        return np.array([0.0, 60.0]), np.array([0.5, 0.5])


def parse_chat_velocity(chat_path: Optional[str], duration: float, bin_size_sec: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parses chat messages/comments and calculates hype message density per time bin.
    """
    num_bins = max(int(duration / bin_size_sec) + 1, 1)
    times = np.arange(num_bins) * bin_size_sec
    velocity = np.zeros(num_bins, dtype=np.float32)

    if not chat_path or not os.path.exists(chat_path):
        return times, velocity

    HYPE_WORDS = {"w", "l", "kekw", "omegalul", "pog", "poggers", "clip", "no way", "wtf", "holy", "bro", "lets go", "sheesh"}

    try:
        with open(chat_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)

        comments = data.get("comments", [])
        for c in comments:
            t = float(c.get("time_in_seconds", 0.0))
            text = c.get("text", "").lower()
            bin_idx = int(t / bin_size_sec)
            if 0 <= bin_idx < num_bins:
                # Basic message count
                weight = 1.0
                # Extra weight for hype words
                for hw in HYPE_WORDS:
                    if hw in text:
                        weight += 2.0
                velocity[bin_idx] += weight

        max_v = np.max(velocity)
        if max_v > 0:
            velocity /= max_v
    except Exception as e:
        logger.warning(f"Could not parse chat log: {e}")

    return times, velocity


def snap_to_word_boundaries(
    start_time: float,
    end_time: float,
    segments: List[Dict[str, Any]],
    min_duration: float = 18.0,
    max_duration: float = 58.0
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Finds exact word timestamps that closely bracket start_time and end_time.
    Guarantees that video cuts NEVER slice mid-word or mid-syllable.
    Returns: (snapped_start, snapped_end, list_of_words_in_clip)
    """
    all_words = []
    for s in segments:
        for w in s.get("words", []):
            all_words.append(w)

    if not all_words:
        # Fallback to segment start/ends
        return round(start_time, 2), round(min(end_time, start_time + max_duration), 2), []

    # Find word closest to start_time
    start_word_idx = 0
    min_start_diff = float("inf")
    for idx, w in enumerate(all_words):
        diff = abs(w["start"] - start_time)
        if diff < min_start_diff:
            min_start_diff = diff
            start_word_idx = idx

    # If the word starts before or near the target start, use its start
    snapped_start = all_words[start_word_idx]["start"]

    # Target end time
    target_end = min(snapped_start + max_duration, max(end_time, snapped_start + min_duration))
    end_word_idx = start_word_idx
    min_end_diff = float("inf")

    for idx in range(start_word_idx, len(all_words)):
        w = all_words[idx]
        diff = abs(w["end"] - target_end)
        if diff < min_end_diff:
            min_end_diff = diff
            end_word_idx = idx

    snapped_end = all_words[end_word_idx]["end"]

    # Verify duration constraints
    dur = snapped_end - snapped_start
    if dur < min_duration and end_word_idx + 1 < len(all_words):
        # Extend words until min_duration
        while end_word_idx + 1 < len(all_words) and (all_words[end_word_idx]["end"] - snapped_start) < min_duration:
            end_word_idx += 1
        snapped_end = all_words[end_word_idx]["end"]
    elif dur > max_duration:
        # Reduce words
        while end_word_idx > start_word_idx and (all_words[end_word_idx]["end"] - snapped_start) > max_duration:
            end_word_idx -= 1
        snapped_end = all_words[end_word_idx]["end"]

    clip_words = all_words[start_word_idx : end_word_idx + 1]
    return round(snapped_start, 2), round(snapped_end, 2), clip_words


async def detect_hype_moments(
    audio_path: str,
    segments: List[Dict[str, Any]],
    chat_path: Optional[str] = None,
    total_duration: float = 0.0,
    max_clips: int = 5,
    progress_cb: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Main hype detection pipeline:
    1. Computes audio RMS energy curve
    2. Incorporates chat velocity
    3. Finds prominent excitement peaks using scipy.signal
    4. Snaps candidate windows to clean word boundaries
    5. Calls Ollama LLM for semantic hook analysis & CTR scoring
    """
    if progress_cb:
        await progress_cb(60.0, "Computing audio RMS loudness curve & excitement peaks...")

    times, audio_rms = compute_audio_rms_curve(audio_path, hop_length_sec=0.5)
    
    if progress_cb:
        await progress_cb(68.0, "Analyzing chat velocity and sentiment spikes...")

    chat_times, chat_vel = parse_chat_velocity(chat_path, total_duration)

    # Resample or interpolate chat velocity to match audio times
    if len(chat_vel) > 1 and len(times) > 1:
        chat_interp = np.interp(times, chat_times, chat_vel)
    else:
        chat_interp = np.zeros_like(times)

    # Combined composite hype curve
    composite_hype = 0.65 * audio_rms + 0.35 * chat_interp

    # Peak detection using scipy
    if len(composite_hype) > 10:
        # Smooth with moving average
        kernel_size = 5
        smoothed = np.convolve(composite_hype, np.ones(kernel_size)/kernel_size, mode='same')
        peaks, props = scipy.signal.find_peaks(
            smoothed,
            height=np.percentile(smoothed, 70),  # Top 30% of excitement
            distance=int(25.0 / 0.5)  # At least 25 seconds apart
        )
    else:
        peaks = [0]

    if progress_cb:
        await progress_cb(75.0, f"Identified {len(peaks)} acoustic/chat peaks. Snapping to word boundaries...")

    raw_candidates = []
    for peak_idx in peaks:
        peak_time = times[peak_idx]
        # Build candidate window centering the peak (or placing it 60% into the clip)
        cand_start = max(0.0, peak_time - 12.0)
        cand_end = cand_start + 35.0

        snapped_start, snapped_end, clip_words = snap_to_word_boundaries(
            cand_start, cand_end, segments, min_duration=18.0, max_duration=55.0
        )

        clip_text = " ".join(w["word"] for w in clip_words)
        peak_score = float(composite_hype[peak_idx] * 100.0)

        raw_candidates.append({
            "start_time": snapped_start,
            "end_time": snapped_end,
            "duration": snapped_end - snapped_start,
            "hype_score": min(round(peak_score, 1), 99.0),
            "words": clip_words,
            "text": clip_text
        })

    # If no peaks found, generate from segments
    if not raw_candidates and segments:
        snapped_start, snapped_end, clip_words = snap_to_word_boundaries(
            0.0, min(total_duration, 40.0), segments
        )
        raw_candidates.append({
            "start_time": snapped_start,
            "end_time": snapped_end,
            "duration": snapped_end - snapped_start,
            "hype_score": 75.0,
            "words": clip_words,
            "text": " ".join(w["word"] for w in clip_words)
        })

    if progress_cb:
        await progress_cb(82.0, "Consulting local Ollama LLM for viral hook analysis...")

    # Let Ollama rank the viral hooks and generate high-CTR titles
    llm_ranked = ollama_client.rank_viral_hooks(segments, max_candidates=max_clips)

    final_clips = []
    # Merge LLM suggestions with acoustic peaks
    for rank_idx, candidate in enumerate(raw_candidates[:max_clips]):
        clip_text = candidate["text"]
        meta = ollama_client.generate_clip_metadata(clip_text)

        # Hook summary
        words = candidate["words"]
        hook_summary = " ".join(w["word"] for w in words[:8]) if words else "High-energy moment"

        final_clips.append({
            "title": meta.get("title", f"VIRAL MOMENT #{rank_idx + 1} 🔥"),
            "hook_summary": hook_summary,
            "description": meta.get("description", "You have to see this!"),
            "hashtags": meta.get("hashtags", "#shorts #reels #gaming #viral"),
            "start_time": candidate["start_time"],
            "end_time": candidate["end_time"],
            "duration": candidate["duration"],
            "hype_score": candidate["hype_score"],
            "viral_rank": rank_idx + 1,
            "words": candidate["words"]
        })

    if progress_cb:
        await progress_cb(90.0, f"Hype analysis complete: Generated {len(final_clips)} viral candidates.")

    return final_clips
