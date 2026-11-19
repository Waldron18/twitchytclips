@echo off
setlocal enabledelayedexpansion
title ClipForge Local Server

echo =====================================================================
echo                Starting ClipForge Local (Port 8000)
echo =====================================================================
echo.

:: 1. Activate Virtual Environment if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: 2. Check if Ollama is running, launch in background if needed
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo Starting Ollama background server...
        start /b ollama serve >nul 2>&1
        timeout /t 2 /nobreak >nul
    ) else (
        echo Ollama server is already running!
    )
)

:: 3. Determine available port (8000 or fallback 8001/8080)
for /f "tokens=*" %%i in ('python -c "from backend.config import SERVER_PORT; print(SERVER_PORT)"') do set CLIP_PORT=%%i
if "%CLIP_PORT%"=="" set CLIP_PORT=8000

:: 4. Automatically open default browser after a brief startup delay
echo Launching browser interface at http://localhost:%CLIP_PORT% ...
start "" http://localhost:%CLIP_PORT%

:: 5. Start Uvicorn / FastAPI server on 0.0.0.0:%CLIP_PORT%
echo.
echo =====================================================================
echo Server active on:
echo   - Local PC:     http://localhost:%CLIP_PORT%
echo   - Local Wi-Fi:  http://0.0.0.0:%CLIP_PORT% (accessible from phones/tablets)
echo Press Ctrl+C in this console to stop the server.
echo =====================================================================
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port %CLIP_PORT%

pause
