"""
main.py - FastAPI application, REST endpoints, WebSocket/SSE streams,
and static file server for ClipForge Local.
"""
import os
import uuid
import json
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import (
    SERVER_HOST, SERVER_PORT, DATA_DIR, TEMP_DIR, EXPORTS_DIR,
    MUSIC_DIR, FRONTEND_DIST, TARGET_LUFS
)
from backend.database import (
    init_db, get_db_session, AsyncSessionLocal,
    ProjectModel, ClipModel, JobModel, SettingModel
)
from backend.hardware_profiler import detect_hardware_profile, get_free_disk_space_gb
from backend.queue_manager import job_queue
from backend.ingest import ingest_media, probe_file_info
from backend.transcribe import run_transcription
from backend.hype_detector import detect_hype_moments
from backend.audio_master import extract_video_segment, process_audio_mastering
from backend.renderer import detect_facecam_box, render_vertical_clip
from backend.ollama_client import ollama_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("clipforge.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB and launch sequential job queue
    logger.info("Initializing ClipForge Local database...")
    await init_db()
    await job_queue.start()
    detect_hardware_profile()
    logger.info("ClipForge Local started successfully.")
    yield
    # Shutdown
    await job_queue.stop()
    logger.info("ClipForge Local shutdown complete.")

app = FastAPI(title="ClipForge Local API", lifespan=lifespan)

# Allow local network access (e.g. from mobile or other PC on local Wi-Fi)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static asset folders for direct browser streaming
app.mount("/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")
app.mount("/temp", StaticFiles(directory=str(TEMP_DIR)), name="temp")
app.mount("/assets/music", StaticFiles(directory=str(MUSIC_DIR)), name="music")

# Pydantic Schemas
class CreateProjectRequest(BaseModel):
    source_url: str
    storage_saver: Optional[bool] = None
    target_clips: int = 5
    live_capture_duration_minutes: Optional[int] = 10

class UpdateClipRequest(BaseModel):
    title: Optional[str] = None
    facecam_rect: Optional[Dict[str, float]] = None
    has_facecam: Optional[bool] = None
    subtitle_style: Optional[str] = None
    bgm_track: Optional[str] = None
    bgm_volume_db: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None

class OverrideTierRequest(BaseModel):
    tier: str

# -------------------------------------------------------------
# Background Pipeline Workflows
# -------------------------------------------------------------

async def run_full_pipeline(project_id: str, source_url: str, storage_saver: Optional[bool], target_clips: int, live_capture_duration_minutes: int = 10, progress_cb=None):
    """
    Executes the complete video-to-clips pipeline strictly sequentially:
    1. Media Ingest (audio first if storage saver; handles live streams or VODs)
    2. faster-whisper transcription & word-level alignment
    3. Hype detection (RMS audio + chat velocity + Ollama hook analysis + word snapping)
    4. Auto facecam scan and candidate clip generation
    """
    project_dir = TEMP_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ProjectModel)
            .where(ProjectModel.id == project_id)
            .values(status="ingesting")
        )
        await session.commit()

    # Step 1: Ingestion
    live_secs = max(60, min(live_capture_duration_minutes * 60, 3600))
    ingest_res = await ingest_media(source_url, project_id, storage_saver_override=storage_saver, live_capture_seconds=live_secs, progress_cb=progress_cb)

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ProjectModel)
            .where(ProjectModel.id == project_id)
            .values(
                title=ingest_res["title"],
                platform=ingest_res["platform"],
                duration=ingest_res["duration"],
                audio_path=ingest_res["audio_path"],
                video_path=ingest_res["video_path"],
                chat_path=ingest_res["chat_path"],
                status="transcribing"
            )
        )
        await session.commit()

    # Step 2: Transcription with word timestamps
    trans_out = str(project_dir / "transcription.json")
    segments = run_transcription(ingest_res["audio_path"], output_json_path=trans_out, progress_cb=progress_cb)

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ProjectModel)
            .where(ProjectModel.id == project_id)
            .values(transcript_path=trans_out, status="analyzing")
        )
        await session.commit()

    # Step 3: Hype Detection & Candidate Generation
    candidates = await detect_hype_moments(
        audio_path=ingest_res["audio_path"],
        segments=segments,
        chat_path=ingest_res["chat_path"],
        total_duration=ingest_res["duration"],
        max_clips=target_clips,
        progress_cb=progress_cb
    )

    # Step 4: Scan for facecam if video available
    detected_cam = {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}
    if ingest_res["video_path"] and os.path.exists(ingest_res["video_path"]):
        if progress_cb:
            await progress_cb(92.0, "Scanning video frames for streamer webcam box...")
        cam = detect_facecam_box(ingest_res["video_path"])
        if cam:
            detected_cam = cam

    # Save generated clips into database
    async with AsyncSessionLocal() as session:
        for c in candidates:
            clip_id = str(uuid.uuid4())
            new_clip = ClipModel(
                id=clip_id,
                project_id=project_id,
                title=c["title"],
                hook_summary=c["hook_summary"],
                description=c["description"],
                hashtags=c["hashtags"],
                start_time=c["start_time"],
                end_time=c["end_time"],
                duration=c["duration"],
                hype_score=c["hype_score"],
                viral_rank=c["viral_rank"],
                facecam_rect=json.dumps(detected_cam),
                has_facecam=True,
                subtitle_style="karaoke_yellow",
                bgm_track="lofi_chill.mp3",
                bgm_volume_db=-24.0,
                words_json=json.dumps(c["words"]),
                status="candidate"
            )
            session.add(new_clip)

        await session.execute(
            update(ProjectModel)
            .where(ProjectModel.id == project_id)
            .values(status="ready")
        )
        await session.commit()

    if progress_cb:
        await progress_cb(100.0, f"Pipeline complete: {len(candidates)} clips ready for review!")


async def run_clip_render_pipeline(clip_id: str, progress_cb=None):
    """
    Renders an individual candidate clip into a finished 1080x1920 9:16 vertical video.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(ClipModel, ProjectModel)
            .join(ProjectModel, ClipModel.project_id == ProjectModel.id)
            .where(ClipModel.id == clip_id)
        )
        row = res.first()
        if not row:
            raise ValueError(f"Clip {clip_id} not found.")
        clip, project = row

        await session.execute(
            update(ClipModel).where(ClipModel.id == clip_id).values(status="rendering")
        )
        await session.commit()

    clip_dir = TEMP_DIR / project.id / f"clip_{clip_id}"
    clip_dir.mkdir(parents=True, exist_ok=True)

    raw_segment_path = str(clip_dir / "raw_segment.mp4")
    mastered_audio_path = str(clip_dir / "mastered_audio.aac")
    output_mp4_name = f"{project.title[:20]}_{clip.viral_rank}_{clip_id[:6]}.mp4".replace(" ", "_")
    output_mp4_path = str(EXPORTS_DIR / output_mp4_name)

    if progress_cb:
        await progress_cb(15.0, "Extracting video segment for candidate time window...")

    # Step 1: Extract Video Segment
    source_to_cut = project.video_path if (project.video_path and os.path.exists(project.video_path)) else project.source_url
    is_local = bool(project.video_path and os.path.exists(project.video_path))
    extract_video_segment(
        source_url_or_path=source_to_cut,
        start_time=clip.start_time,
        end_time=clip.end_time,
        output_path=raw_segment_path,
        is_local_file=is_local
    )

    if progress_cb:
        await progress_cb(40.0, "Isolating speech & mixing copyright-safe background music (-14 LUFS)...")

    # Step 2: Audio mastering & Loudnorm
    process_audio_mastering(
        raw_video_path=raw_segment_path,
        output_audio_path=mastered_audio_path,
        bgm_filename=clip.bgm_track,
        bgm_volume_db=clip.bgm_volume_db,
        isolate_vocals=True
    )

    if progress_cb:
        await progress_cb(65.0, "Synthesizing animated karaoke subtitles & encoding 9:16 vertical video...")

    # Step 3: Render 9:16 Canvas with Burned Subtitles
    words_data = json.loads(clip.words_json) if clip.words_json else []
    facecam_data = json.loads(clip.facecam_rect) if clip.facecam_rect else None

    render_vertical_clip(
        video_segment_path=raw_segment_path,
        mastered_audio_path=mastered_audio_path,
        output_mp4_path=output_mp4_path,
        facecam_rect=facecam_data,
        has_facecam=clip.has_facecam,
        words=words_data,
        clip_start_offset=clip.start_time,
        subtitle_style=clip.subtitle_style,
        progress_cb=progress_cb
    )

    # Relative export path for web serving
    rel_export_url = f"/exports/{Path(output_mp4_path).name}"

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ClipModel)
            .where(ClipModel.id == clip_id)
            .values(
                rendered_video_path=rel_export_url,
                status="ready"
            )
        )
        await session.commit()

    # If storage saver enabled, clean raw segment
    profile = detect_hardware_profile()
    if profile.storage_saver_mode and os.path.exists(raw_segment_path):
        try:
            os.remove(raw_segment_path)
            if os.path.exists(mastered_audio_path):
                os.remove(mastered_audio_path)
        except Exception:
            pass

    if progress_cb:
        await progress_cb(100.0, "Clip successfully rendered!")


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.get("/api/hardware")
async def get_hardware_info():
    """Returns detected hardware profile, system specs, and recommendations."""
    prof = detect_hardware_profile()
    return prof.to_dict()

@app.post("/api/hardware/override")
async def override_hardware_tier(body: OverrideTierRequest):
    """Allows manual override of hardware profile tier."""
    prof = detect_hardware_profile(force_refresh=True, override_tier=body.tier)
    return prof.to_dict()

@app.get("/api/ollama/status")
async def get_ollama_status():
    """Checks if Ollama REST server is reachable and lists models."""
    online = ollama_client.is_online()
    models = ollama_client.get_installed_models() if online else []
    profile = detect_hardware_profile()
    return {
        "online": online,
        "base_url": ollama_client.base_url,
        "recommended_model": profile.ollama_model,
        "installed_models": models
    }

@app.post("/api/ollama/pull")
async def pull_ollama_model(model: Optional[str] = None):
    profile = detect_hardware_profile()
    target_model = model or profile.ollama_model
    success = ollama_client.pull_model(target_model)
    return {"model": target_model, "success": success}

@app.post("/api/projects/create")
async def create_project(body: CreateProjectRequest, db: AsyncSession = Depends(get_db_session)):
    """Creates a project and enqueues full ingestion and hype detection."""
    project_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    new_project = ProjectModel(
        id=project_id,
        source_url=body.source_url,
        status="created"
    )
    db.add(new_project)
    await db.commit()

    # Enqueue pipeline
    await job_queue.submit_job(
        job_id,
        project_id,
        None,
        "pipeline",
        run_full_pipeline,
        project_id=project_id,
        source_url=body.source_url,
        storage_saver=body.storage_saver,
        target_clips=body.target_clips,
        live_capture_duration_minutes=body.live_capture_duration_minutes or 10
    )

    return {"project_id": project_id, "job_id": job_id, "status": "enqueued"}


@app.post("/api/projects/upload")
async def upload_local_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db_session)):
    """Handles local video file upload from desktop browser."""
    project_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    project_dir = TEMP_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    dest_file = project_dir / file.filename
    with open(dest_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    new_project = ProjectModel(
        id=project_id,
        source_url=str(dest_file),
        title=Path(file.filename).stem,
        status="created"
    )
    db.add(new_project)
    await db.commit()

    # Enqueue pipeline
    await job_queue.submit_job(
        job_id,
        project_id,
        None,
        "pipeline",
        run_full_pipeline,
        project_id=project_id,
        source_url=str(dest_file),
        storage_saver=False,
        target_clips=5
    )

    return {"project_id": project_id, "job_id": job_id, "status": "enqueued"}


@app.get("/api/projects")
async def list_projects(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(select(ProjectModel).order_by(ProjectModel.created_at.desc()))
    projects = res.scalars().all()
    return [p.to_dict() for p in projects]

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    res_clips = await db.execute(
        select(ClipModel).where(ClipModel.project_id == project_id).order_by(ClipModel.viral_rank)
    )
    clips = res_clips.scalars().all()

    data = project.to_dict()
    data["clips"] = [c.to_dict() for c in clips]
    return data

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db_session)):
    # Delete folder in temp
    p_dir = TEMP_DIR / project_id
    if p_dir.exists():
        shutil.rmtree(p_dir, ignore_errors=True)

    await db.execute(delete(ProjectModel).where(ProjectModel.id == project_id))
    await db.commit()
    return {"status": "deleted"}

@app.put("/api/clips/{clip_id}")
async def update_clip(clip_id: str, body: UpdateClipRequest, db: AsyncSession = Depends(get_db_session)):
    """Updates clip parameters (facecam crop coordinates, deleted words, title, BGM)."""
    res = await db.execute(select(ClipModel).where(ClipModel.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if body.title is not None:
        clip.title = body.title
    if body.facecam_rect is not None:
        clip.facecam_rect = json.dumps(body.facecam_rect)
    if body.has_facecam is not None:
        clip.has_facecam = body.has_facecam
    if body.subtitle_style is not None:
        clip.subtitle_style = body.subtitle_style
    if body.bgm_track is not None:
        clip.bgm_track = body.bgm_track
    if body.bgm_volume_db is not None:
        clip.bgm_volume_db = body.bgm_volume_db
    if body.words is not None:
        clip.words_json = json.dumps(body.words)

    await db.commit()
    return clip.to_dict()

@app.post("/api/clips/{clip_id}/render")
async def trigger_clip_render(clip_id: str, db: AsyncSession = Depends(get_db_session)):
    """Enqueues 9:16 vertical video rendering for a candidate clip."""
    res = await db.execute(select(ClipModel).where(ClipModel.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    job_id = str(uuid.uuid4())
    await job_queue.submit_job(
        job_id,
        clip.project_id,
        clip_id,
        "render",
        run_clip_render_pipeline,
        clip_id=clip_id
    )

    return {"job_id": job_id, "status": "queued"}

@app.get("/api/music/tracks")
async def list_music_tracks():
    """Lists built-in royalty-free audio tracks."""
    tracks = []
    if MUSIC_DIR.exists():
        for file in MUSIC_DIR.glob("*.mp3"):
            tracks.append({
                "filename": file.name,
                "name": file.stem.replace("_", " ").title(),
                "url": f"/assets/music/{file.name}"
            })
    return tracks

@app.get("/api/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(select(JobModel).order_by(JobModel.created_at.desc()).limit(20))
    jobs = res.scalars().all()
    return [j.to_dict() for j in jobs]

@app.get("/api/jobs/stream")
async def stream_job_events():
    """Server-Sent Events (SSE) endpoint for real-time progress updates."""
    sub_queue = job_queue.subscribe()

    async def event_generator():
        try:
            while True:
                data = await sub_queue.get()
                yield f"data: {data}\n\n"
        except Exception:
            pass
        finally:
            job_queue.unsubscribe(sub_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/system/cleanup")
async def get_cleanup_stats():
    """Calculates disk usage of raw temp files vs final exported clips."""
    temp_bytes = 0
    for root, _, files in os.walk(TEMP_DIR):
        for f in files:
            temp_bytes += os.path.getsize(os.path.join(root, f))

    export_bytes = 0
    for root, _, files in os.walk(EXPORTS_DIR):
        for f in files:
            export_bytes += os.path.getsize(os.path.join(root, f))

    free_disk = get_free_disk_space_gb()

    return {
        "temp_usage_mb": round(temp_bytes / (1024 * 1024), 2),
        "exports_usage_mb": round(export_bytes / (1024 * 1024), 2),
        "free_disk_gb": free_disk
    }

@app.post("/api/system/cleanup")
async def execute_cleanup():
    """One-click cleanup of all raw video segments and intermediate caches."""
    cleaned_bytes = 0
    for item in TEMP_DIR.iterdir():
        try:
            if item.is_dir():
                # calculate size
                for root, _, files in os.walk(item):
                    for f in files:
                        cleaned_bytes += os.path.getsize(os.path.join(root, f))
                shutil.rmtree(item, ignore_errors=True)
            else:
                cleaned_bytes += item.stat().st_size
                item.unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "status": "cleaned",
        "freed_mb": round(cleaned_bytes / (1024 * 1024), 2),
        "current_free_disk_gb": get_free_disk_space_gb()
    }

# -------------------------------------------------------------
# Frontend Static Files Serving & SPA Fallback
# -------------------------------------------------------------
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve index.html for frontend routing
        index_file = FRONTEND_DIST / "index.html"
        requested = FRONTEND_DIST / full_path
        if requested.exists() and requested.is_file():
            return FileResponse(requested)
        return FileResponse(index_file)
else:
    @app.get("/")
    async def root_placeholder():
        return {
            "name": "ClipForge Local API",
            "status": "online",
            "message": "Frontend is building or running on Vite dev server."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
