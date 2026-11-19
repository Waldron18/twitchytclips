"""
transcribe.py - Hardware-accelerated word-level speech alignment using faster-whisper.
Enforces strict memory management: unloads Whisper model and frees GPU cache immediately.
"""
import os
import gc
import json
import logging
from typing import Optional, Dict, Any, List
from backend.hardware_profiler import detect_hardware_profile

logger = logging.getLogger("clipforge.transcribe")

def unload_whisper(model):
    """
    Strict memory cleanup: deletes model and clears PyTorch CUDA memory cache
    so Ollama and Whisper never compete for VRAM simultaneously.
    """
    if model is not None:
        try:
            del model
        except Exception:
            pass

    gc.collect()

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.info("Cleared PyTorch CUDA VRAM cache.")
    except Exception:
        pass


def load_audio_waveform(audio_path: str) -> "np.ndarray":
    """
    Decodes and resamples audio to 16kHz mono float32 array using FFmpeg.
    Avoids PyAV container errors and works across all container formats.
    """
    import subprocess
    import numpy as np
    cmd = [
        "ffmpeg", "-y", "-loglevel", "quiet",
        "-i", audio_path,
        "-f", "s16le",
        "-ac", "1",
        "-ar", "16000",
        "-"
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(proc.stdout, dtype=np.int16).flatten().astype(np.float32) / 32768.0


def run_transcription(
    audio_path: str,
    output_json_path: Optional[str] = None,
    language: Optional[str] = None,
    progress_cb: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Runs faster-whisper with word-level timestamps enabled.
    Returns list of segments with word timestamps and saves to JSON.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    from faster_whisper import WhisperModel

    profile = detect_hardware_profile()
    model_size = profile.whisper_model
    compute_type = profile.whisper_compute_type
    device = profile.whisper_device

    logger.info(f"Loading faster-whisper '{model_size}' on device '{device}' ({compute_type})...")
    if progress_cb:
        progress_cb(5.0, f"Loading Whisper model ({model_size}) on {device.upper()}...")

    model = None
    try:
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            logger.warning(f"Failed to load Whisper on {device} ({e}). Falling back to CPU int8...")
            if progress_cb:
                progress_cb(10.0, "Falling back to CPU Whisper (safe mode)...")
            model = WhisperModel("small.en", device="cpu", compute_type="int8")

        if progress_cb:
            progress_cb(20.0, "Transcribing speech & aligning word boundaries...")

        # Decode audio waveform directly via FFmpeg to bypass PyAV version quirks
        audio_array = load_audio_waveform(audio_path)

        # Run transcription with word timestamps on waveform array
        segments_generator, info = model.transcribe(
            audio_array,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            language=language
        )

        segments = []
        seg_idx = 0

        for seg in segments_generator:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3)
                    })

            segments.append({
                "id": seg_idx,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words
            })
            seg_idx += 1

            if progress_cb and info.duration > 0:
                pct = min(20.0 + (seg.end / info.duration) * 70.0, 92.0)
                progress_cb(pct, f"Transcribing [{round(seg.end, 1)}s / {round(info.duration, 1)}s]...")

        logger.info(f"Transcription complete: {len(segments)} segments aligned.")

        if output_json_path:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)

        if progress_cb:
            progress_cb(95.0, "Unloading Whisper model to free memory for Ollama...")

        return segments

    finally:
        # STRICT MEMORY UNLOAD
        unload_whisper(model)
        if progress_cb:
            progress_cb(100.0, "Transcription & alignment complete.")
