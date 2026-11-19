# ClipForge Local ⚡

> **100% Free & Open-Source Local AI Video Clipping Desktop / Web Application**  
> Output vertical 9:16 short-form clips (`1080x1920`) optimized for **YouTube Shorts** and **Instagram Reels** with facecam split-screen framing, word-by-word animated karaoke captions, dead-air trimming, and copyright-safe background audio replacement. **$0 API Cost — Zero Cloud Lock-in.**

---

## 🚀 Key Features

- **Hardware Auto-Scaling (`LOW` / `MID` / `HIGH`):** Automatically benchmarks GPU, VRAM, System RAM, and hardware NVENC encoding on startup and auto-configures Whisper and LLM models without user intervention.
- **Strict GPU Memory Management:** Automatically unloads Whisper from VRAM (`del model; gc.collect(); torch.cuda.empty_cache()`) before invoking the local LLM brain so Whisper and Ollama never compete for VRAM simultaneously.
- **Storage Saver Mode:** Designed specifically for low-storage machines (~8–11 GB free disk space). Ingests audio-first (`.m4a`) to minimize disk space and extracts 60s video segments only for candidate clips, with a one-click temp cache purger.
- **Smart 9:16 Facecam Split-Screen Framing:** OpenCV webcam bounding-box detection automatically frames streamer facecams to the top 35% (`1080x672`) and gameplay to the bottom 65% (`1080x1248`), with real-time UI crop controls and single-crop / blur fallback.
- **Animated Karaoke Subtitles (`.ass`):** Word-accurate timestamped captions generated via `faster-whisper` and burned into the video with active-word color pop and scale animation.
- **Multi-Modal Hype & Hook Detection:** Combines audio RMS volume peaks (`librosa` / `scipy`), chat velocity velocity spikes (`W`, `KEKW`, `CLIP IT`), and local Ollama LLM prompt scoring.
- **Clean Word Boundary Snapping:** Start and end timestamps automatically snap to clean word boundaries so dialogue is never cut off mid-sentence or mid-syllable.
- **Copyright-Safe Audio Replacement:** Strips copyrighted background audio, optionally mixes built-in royalty-free Lo-Fi / Upbeat music at `-24 dB`, and masters output to `-14 LUFS` standard.
- **Dead-Air & Filler Word Trimming:** Interactive transcript editor where creators can click words to strike them out and auto-trim pauses.

---

## 🖥️ Hardware Auto-Scaling Tiers

`hardware_profiler.py` automatically evaluates the host PC on startup:

| Tier | Hardware Target | Whisper Speech Model | Ollama LLM Brain | FFmpeg Video Encoder | Storage Mode |
|---|---|---|---|---|---|
| **`LOW`** | < 3 GB VRAM or no NVENC *(e.g. MX150, 8 GB RAM, iGPU)* | `small.en` (`compute_type="int8"`, CPU safe) | `qwen2.5:1.5b` *(or rule-based NLP)* | `libx264 -preset veryfast -crf 23` | **Storage Saver Enabled** (Audio-first, auto-scrub) |
| **`MID`** | 3 GB – 5.9 GB VRAM with NVENC *(e.g. GTX 1060 3GB, RTX 3050 4GB)* | `large-v3-turbo` (`compute_type="int8"`, CUDA) | `qwen3.5:4b` | `h264_nvenc -preset p4 -cq 22` | Standard |
| **`HIGH`** | 6 GB+ VRAM with NVENC *(e.g. GTX 1060 6GB, RTX 3050 8GB, RTX 4060+)* | `large-v3-turbo` (`compute_type="int8_float16"`, CUDA) | `qwen3.5:9b` | `h264_nvenc -preset p5 -cq 20` | Full Quality |

---

## 🛠️ Quick Start (Windows)

### 1. One-Click Setup
Double-click `setup.bat` or run:
```bat
setup.bat
```
This script will:
1. Verify Python (3.10+) and FFmpeg in PATH.
2. Create and activate a Python virtual environment (`.\venv`).
3. Install backend dependencies (`requirements.txt`).
4. Generate built-in royalty-free background music tracks (`scripts/generate_bgm.py`).
5. Build the React 18 + Vite frontend bundle to `frontend/dist`.
6. Query Ollama and pull the appropriate model for your detected hardware tier.

### 2. Launching ClipForge Local
Double-click `start.bat` or run:
```bat
start.bat
```
- Starts the FastAPI backend and static asset server.
- Automatically launches your default web browser to `http://localhost:8000` (or fallback `http://localhost:8001`).
- Accessible across your local Wi-Fi from mobile phones or tablets via `http://<your-lan-ip>:8000`.

---

## 📂 Project Architecture

```
clip/
├── backend/
│   ├── config.py             # Paths, server port, loudness targets
│   ├── hardware_profiler.py  # GPU, VRAM, RAM, NVENC probe & LOW/MID/HIGH tier assigner
│   ├── database.py           # SQLite aiosqlite / SQLAlchemy async models
│   ├── queue_manager.py      # Strictly sequential GPU task queue (prevents VRAM OOM)
│   ├── ingest.py             # YouTube, Twitch, Kick (audio-first) and local file ingest
│   ├── transcribe.py         # faster-whisper word-level alignment & VRAM memory unloader
│   ├── hype_detector.py      # RMS volume curve + chat spikes + Ollama hook analysis + word snapping
│   ├── audio_master.py       # Audio extraction, copyright stripping, BGM mixing, -14 LUFS loudnorm
│   ├── renderer.py           # OpenCV facecam detector, 9:16 split-screen canvas, .ass karaoke subtitles
│   ├── ollama_client.py      # Local Ollama REST client (with rule-based NLP fallback)
│   └── main.py               # FastAPI application & static file server
├── frontend/
│   ├── src/
│   │   ├── components/       # Navbar, HardwareModal, IngestModal, FacecamAdjuster, TranscriptEditor, etc.
│   │   ├── services/api.ts   # REST and SSE client
│   │   └── App.tsx           # Creator dashboard
│   ├── dist/                 # Production prebuilt static bundle served by FastAPI
│   └── package.json
├── assets/
│   └── music/                # Royalty-free background audio tracks (lofi_chill.mp3, upbeat_hype.mp3)
├── scripts/
│   ├── generate_bgm.py       # Synthetic harmonic BGM generator
│   ├── test_pipeline.py      # 8-step integration test suite
│   └── test_e2e_api.py       # End-to-end REST API pipeline test
├── setup.bat                 # One-click Windows setup script
├── start.bat                 # One-click Windows launch script
└── requirements.txt
```

---

## 🧪 Running Verification Tests

Run the full automated integration test suite:
```powershell
python scripts/test_pipeline.py
```
This tests:
- Hardware auto-profiler detection
- Royalty-free BGM presence
- Animated karaoke `.ass` subtitle generator
- Synthetic 16:9 test video generation
- OpenCV streamer facecam detection
- Audio mastering with BGM and `-14 LUFS` normalization
- 9:16 vertical short render (`1080x1920`)
- Viral hook & metadata generation

Run the end-to-end API pipeline test:
```powershell
python scripts/test_e2e_api.py
```

---

## 🔒 License & Philosophy

ClipForge Local is 100% Free & Open-Source under the MIT License. Zero paid API keys, zero cloud subscriptions, zero telemetry.
