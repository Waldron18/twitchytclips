"""
hardware_profiler.py - Intelligent hardware detection & dynamic tier scaling for ClipForge Local.
Detects GPU, VRAM, System RAM, NVENC support, and free disk space.
Automatically assigns tiers: LOW, MID, HIGH.
"""
import os
import shutil
import subprocess
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import psutil

logger = logging.getLogger("clipforge.hardware")

@dataclass
class HardwareProfile:
    tier: str  # "LOW", "MID", "HIGH"
    gpu_name: str
    vram_gb: float
    ram_gb: float
    has_nvenc: bool
    whisper_model: str
    whisper_compute_type: str
    whisper_device: str
    ollama_model: str
    ffmpeg_video_encoder: str
    ffmpeg_encoder_params: list[str]
    storage_saver_mode: bool
    free_disk_gb: float
    recommendations: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_nvenc_encoder() -> bool:
    """
    Directly tests whether FFmpeg can actually encode with h264_nvenc on this GPU.
    Avoids false positives from `ffmpeg -encoders` where the binary supports NVENC
    but the physical GPU lacks an NVENC block (e.g. MX150 / GT 1030).
    """
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1",
        "-c:v", "h264_nvenc",
        "-f", "null", "-"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception as e:
        logger.debug(f"NVENC probe failed: {e}")
        return False


def get_gpu_info() -> tuple[str, float]:
    """
    Attempts to detect GPU name and total VRAM in Gigabytes.
    Uses nvidia-smi, then PyTorch, then Windows WMI fallback.
    """
    gpu_name = "Unknown / Integrated GPU"
    vram_gb = 0.0

    # Method 1: nvidia-smi
    try:
        smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if smi.returncode == 0 and smi.stdout.strip():
            line = smi.stdout.strip().split("\n")[0]
            parts = line.split(",")
            if len(parts) >= 2:
                gpu_name = parts[0].strip()
                vram_mb = float(parts[1].strip())
                vram_gb = round(vram_mb / 1024.0, 2)
                return gpu_name, vram_gb
    except Exception:
        pass

    # Method 2: torch.cuda
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram_gb = round(props.total_memory / (1024**3), 2)
            return gpu_name, vram_gb
    except Exception:
        pass

    # Method 3: Windows PowerShell CIM / WMI
    try:
        wmi = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=3
        )
        if wmi.returncode == 0 and wmi.stdout.strip():
            names = [n.strip() for n in wmi.stdout.strip().splitlines() if n.strip()]
            for name in names:
                if "nvidia" in name.lower() or "radeon" in name.lower():
                    gpu_name = name
                    break
            else:
                gpu_name = names[0]
    except Exception:
        pass

    return gpu_name, vram_gb


def get_free_disk_space_gb(path: str = ".") -> float:
    """Returns free disk space in GB for the drive containing path."""
    try:
        total, used, free = shutil.disk_usage(path)
        return round(free / (1024**3), 2)
    except Exception:
        return 0.0


# Cached profile instance
_CURRENT_PROFILE: Optional[HardwareProfile] = None

def detect_hardware_profile(force_refresh: bool = False, override_tier: Optional[str] = None) -> HardwareProfile:
    """
    Evaluates system hardware and assigns a profile (LOW, MID, or HIGH).
    Rules:
      LOW:  < 3 GB VRAM or no NVENC (e.g. MX150 / 8 GB RAM / iGPU)
      MID:  3 GB <= VRAM < 6 GB with NVENC (e.g. GTX 1060 3GB / RTX 3050 4GB)
      HIGH: >= 6 GB VRAM with NVENC (e.g. GTX 1060 6GB / RTX 3050 8GB / RTX 4060)
    """
    global _CURRENT_PROFILE
    if _CURRENT_PROFILE is not None and not force_refresh and not override_tier:
        return _CURRENT_PROFILE

    gpu_name, vram_gb = get_gpu_info()
    has_nvenc = check_nvenc_encoder()
    
    # System RAM in GB
    vm = psutil.virtual_memory()
    ram_gb = round(vm.total / (1024**3), 2)
    free_disk_gb = get_free_disk_space_gb()

    # Determine Tier
    recommendations = []
    
    if override_tier and override_tier.upper() in ["LOW", "MID", "HIGH"]:
        tier = override_tier.upper()
        recommendations.append(f"Profile manually overridden to {tier}.")
    else:
        if vram_gb < 3.0 or not has_nvenc:
            tier = "LOW"
        elif 3.0 <= vram_gb < 6.0 and has_nvenc:
            tier = "MID"
        else:
            tier = "HIGH"

    # Profile specifications
    if tier == "LOW":
        whisper_model = "small.en"
        # On low spec (e.g. MX150 / CPU), int8 on CPU or int8 on CUDA if torch allows
        whisper_compute_type = "int8"
        whisper_device = "cpu"  # CPU is safer and won't crash on 2GB MX150 CUDA 11.1
        ollama_model = "qwen2.5:1.5b"
        ffmpeg_video_encoder = "libx264"
        ffmpeg_encoder_params = ["-preset", "veryfast", "-crf", "23"]
        storage_saver_mode = True
        recommendations.append("Low-spec mode enabled: Using CPU Whisper (small.en) and x264 veryfast encoding.")
        recommendations.append("Storage Saver active: Audio-first ingestion + auto temp cleanup.")
        if free_disk_gb < 12.0:
            recommendations.append(f"Low free disk space detected ({free_disk_gb} GB). Aggressive temp scrubbing will run after each clip.")

    elif tier == "MID":
        whisper_model = "large-v3-turbo"  # Fast, highly accurate, low footprint
        whisper_compute_type = "int8"
        whisper_device = "cuda"
        ollama_model = "qwen3.5:4b"
        ffmpeg_video_encoder = "h264_nvenc"
        ffmpeg_encoder_params = ["-preset", "p4", "-cq", "22"]
        storage_saver_mode = False
        recommendations.append("Mid-spec mode active: Hardware NVENC acceleration and int8 Whisper enabled.")

    else:  # HIGH
        whisper_model = "large-v3-turbo"
        whisper_compute_type = "int8_float16"
        whisper_device = "cuda"
        ollama_model = "qwen3.5:9b"
        ffmpeg_video_encoder = "h264_nvenc"
        ffmpeg_encoder_params = ["-preset", "p5", "-cq", "20"]
        storage_saver_mode = False
        recommendations.append("High-spec mode active: Full NVENC p5 high-quality render & 9B LLM viral hook detection.")

    profile = HardwareProfile(
        tier=tier,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        ram_gb=ram_gb,
        has_nvenc=has_nvenc,
        whisper_model=whisper_model,
        whisper_compute_type=whisper_compute_type,
        whisper_device=whisper_device,
        ollama_model=ollama_model,
        ffmpeg_video_encoder=ffmpeg_video_encoder,
        ffmpeg_encoder_params=ffmpeg_encoder_params,
        storage_saver_mode=storage_saver_mode,
        free_disk_gb=free_disk_gb,
        recommendations=recommendations
    )
    _CURRENT_PROFILE = profile
    logger.info(f"Hardware Profile detected: {tier} (GPU: {gpu_name}, VRAM: {vram_gb}GB, NVENC: {has_nvenc})")
    return profile


if __name__ == "__main__":
    prof = detect_hardware_profile(force_refresh=True)
    import json
    print(json.dumps(prof.to_dict(), indent=2))
