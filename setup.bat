@echo off
setlocal enabledelayedexpansion
title ClipForge Local - Windows One-Click Setup

echo =====================================================================
echo           ClipForge Local - Free & Open-Source AI Video Clipper
echo =====================================================================
echo.

:: 1. Check for Python
echo [1/6] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10, 3.12, or newer from https://www.python.org/
    pause
    exit /b 1
)
python --version

:: 2. Check for FFmpeg
echo.
echo [2/6] Checking FFmpeg installation...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] FFmpeg is not found in PATH!
    echo Please download FFmpeg and add the 'bin' folder to your system PATH:
    echo https://ffmpeg.org/download.html or run 'winget install Gyan.FFmpeg'
    pause
    exit /b 1
)
ffmpeg -version | findstr /C:"ffmpeg version"

:: 3. Setup Python Virtual Environment
echo.
echo [3/6] Setting up Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Created virtual environment in .\venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

:: 4. Install Python Dependencies
echo.
echo [4/6] Installing backend dependencies from requirements.txt...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some pip wheels may have encountered warnings. Continuing...
)

:: 5. Generate Built-in BGM Assets
echo.
echo [5/6] Generating royalty-free background audio tracks...
python scripts\generate_bgm.py

:: 6. Check Node.js and build Frontend
echo.
echo [6/6] Checking Node.js and building web frontend...
where npm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    cd frontend
    if not exist "node_modules" (
        echo Installing frontend node packages...
        call npm install
    )
    echo Building production static bundle...
    call npm run build
    cd ..
) else (
    echo [WARNING] Node.js / npm not found. If dist folder exists, prebuilt assets will be used.
)

:: 7. Check Ollama and Pull Recommended Model
echo.
echo =====================================================================
echo Checking Local Ollama Brain...
echo =====================================================================
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Ollama detected on system!
    echo Determining hardware tier to pull optimal model...
    python -c "from backend.hardware_profiler import detect_hardware_profile; p = detect_hardware_profile(); print(f'Target model: {p.ollama_model}'); import subprocess; subprocess.run(['ollama', 'pull', p.ollama_model])"
) else (
    echo [NOTICE] Ollama command line was not found on PATH.
    echo ClipForge Local will use its built-in rule-based NLP fallback engine.
    echo If you wish to use local LLMs (Qwen 1.5B/4B/9B), install Ollama from:
    echo https://ollama.com/
)

echo.
echo =====================================================================
echo [SUCCESS] ClipForge Local setup completed successfully!
echo You can now launch the application anytime using start.bat
echo =====================================================================
pause
