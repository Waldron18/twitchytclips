"""
config.py - Core configuration and directory paths for ClipForge Local.
"""
from pathlib import Path
import os

# Root directory of ClipForge
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

# Application directories
DATA_DIR = ROOT_DIR / "data"
TEMP_DIR = ROOT_DIR / "temp"
EXPORTS_DIR = ROOT_DIR / "exports"
ASSETS_DIR = ROOT_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

# Ensure all critical folders exist
for folder in [DATA_DIR, TEMP_DIR, EXPORTS_DIR, ASSETS_DIR, MUSIC_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'clipforge.db'}"
DATABASE_FILE = DATA_DIR / "clipforge.db"

def find_available_port(preferred_port: int = 8000) -> int:
    import socket
    env_port = os.getenv("CLIPFORGE_PORT")
    if env_port:
        return int(env_port)
    for p in [preferred_port, 8001, 8080, 8888]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('0.0.0.0', p))
            s.close()
            return p
        except Exception:
            continue
    return preferred_port

# Server configuration
SERVER_HOST = os.getenv("CLIPFORGE_HOST", "0.0.0.0")
SERVER_PORT = find_available_port(8000)

# Ollama REST API
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Video Standards
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30  # Default 30fps (60fps configurable in settings)
TARGET_LUFS = -14.0  # Industry standard for YouTube Shorts and Instagram Reels
AUDIO_SAMPLE_RATE = 44100
