"""
database.py - SQLite models & database session management for ClipForge Local.
Uses SQLAlchemy with aiosqlite for non-blocking asynchronous operations.
"""
from datetime import datetime, timezone
import json
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import DATABASE_URL, DATABASE_FILE

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), default="Untitled Video")
    source_url = Column(Text, nullable=False)
    platform = Column(String(50), default="unknown")
    duration = Column(Float, default=0.0)
    audio_path = Column(Text, nullable=True)
    video_path = Column(Text, nullable=True)
    chat_path = Column(Text, nullable=True)
    transcript_path = Column(Text, nullable=True)
    status = Column(String(50), default="created")  # created, ingesting, transcribing, analyzing, ready, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    clips = relationship("ClipModel", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    jobs = relationship("JobModel", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self) -> Dict[str, Any]:
        count = 0
        if "clips" in self.__dict__ and self.clips is not None:
            count = len(self.clips)
        return {
            "id": self.id,
            "title": self.title,
            "source_url": self.source_url,
            "platform": self.platform,
            "duration": self.duration,
            "audio_path": self.audio_path,
            "video_path": self.video_path,
            "has_chat": bool(self.chat_path),
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "clip_count": count
        }


class ClipModel(Base):
    __tablename__ = "clips"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="Viral Clip")
    hook_summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    hashtags = Column(Text, default="#shorts #reels #gaming #viral")
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    hype_score = Column(Float, default=50.0)
    viral_rank = Column(Integer, default=1)
    facecam_rect = Column(Text, default=json.dumps({"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}))
    has_facecam = Column(Boolean, default=True)
    subtitle_style = Column(String(50), default="karaoke_yellow")  # karaoke_yellow, clean_white, neon_green
    bgm_track = Column(String(100), default="lofi_chill.mp3")  # lofi_chill.mp3, upbeat_hype.mp3, none
    bgm_volume_db = Column(Float, default=-24.0)
    rendered_video_path = Column(Text, nullable=True)
    status = Column(String(50), default="candidate")  # candidate, rendering, ready, failed
    error_message = Column(Text, nullable=True)
    words_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    project = relationship("ProjectModel", back_populates="clips")

    def to_dict(self) -> Dict[str, Any]:
        try:
            facecam = json.loads(self.facecam_rect) if self.facecam_rect else None
        except Exception:
            facecam = None

        try:
            words = json.loads(self.words_json) if self.words_json else []
        except Exception:
            words = []

        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "hook_summary": self.hook_summary,
            "description": self.description,
            "hashtags": self.hashtags,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 2),
            "hype_score": round(self.hype_score, 1),
            "viral_rank": self.viral_rank,
            "facecam_rect": facecam,
            "has_facecam": self.has_facecam,
            "subtitle_style": self.subtitle_style,
            "bgm_track": self.bgm_track,
            "bgm_volume_db": self.bgm_volume_db,
            "rendered_video_path": self.rendered_video_path,
            "has_rendered": bool(self.rendered_video_path),
            "status": self.status,
            "error_message": self.error_message,
            "words": words,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    clip_id = Column(String(36), nullable=True)
    job_type = Column(String(50), nullable=False)  # pipeline, ingest, transcribe, hype, render
    status = Column(String(50), default="queued")  # queued, running, completed, failed
    progress = Column(Float, default=0.0)
    current_step = Column(String(255), default="Queued")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    project = relationship("ProjectModel", back_populates="jobs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "clip_id": self.clip_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": round(self.progress, 1),
            "current_step": self.current_step,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class SettingModel(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)


# Async SQLAlchemy setup
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initializes SQLite database and tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session():
    """Dependency for FastAPI route handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
