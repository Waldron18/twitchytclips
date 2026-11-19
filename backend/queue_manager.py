"""
queue_manager.py - Persistent, strictly-sequential GPU/CPU job runner for ClipForge Local.
Ensures that heavy tasks (Whisper transcription, Ollama LLM queries, and FFmpeg video encodes)
run sequentially so VRAM never overflows.
"""
import asyncio
import logging
import traceback
from typing import Callable, Coroutine, Dict, Any, Optional
from datetime import datetime, timezone
import json
from sqlalchemy import select, update
from backend.database import AsyncSessionLocal, JobModel

logger = logging.getLogger("clipforge.queue")

class JobQueueManager:
    def __init__(self):
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._current_job_id: Optional[str] = None
        # In-memory subscriber queues for SSE / live updates
        self._subscribers: list[asyncio.Queue] = []

    async def start(self):
        """Starts the sequential background worker."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._process_loop())
            logger.info("JobQueueManager background worker started.")

    async def stop(self):
        """Stops the worker gracefully."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("JobQueueManager stopped.")

    def subscribe(self) -> asyncio.Queue:
        """Returns an async queue that receives all job progress events."""
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Sends an event message to all active SSE subscribers."""
        payload = json.dumps({"event": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for d in dead:
            self.unsubscribe(d)

    async def submit_job(
        self,
        _job_id: str,
        _project_id: Optional[str],
        _clip_id: Optional[str],
        _job_type: str,
        _func: Callable[..., Coroutine],
        *args,
        **kwargs
    ):
        """Submits a job to the queue and records it in the database."""
        async with AsyncSessionLocal() as session:
            job = JobModel(
                id=_job_id,
                project_id=_project_id,
                clip_id=_clip_id,
                job_type=_job_type,
                status="queued",
                progress=0.0,
                current_step="Queued in line..."
            )
            session.add(job)
            await session.commit()

        await self.broadcast_event("job_queued", {
            "job_id": _job_id,
            "project_id": _project_id,
            "clip_id": _clip_id,
            "job_type": _job_type,
            "status": "queued",
            "progress": 0.0,
            "current_step": "Queued in line..."
        })

        await self._queue.put({
            "job_id": _job_id,
            "project_id": _project_id,
            "clip_id": _clip_id,
            "job_type": _job_type,
            "func": _func,
            "args": args,
            "kwargs": kwargs
        })
        logger.info(f"Job {_job_id} ({_job_type}) enqueued.")

    async def update_job_progress(self, job_id: str, progress: float, current_step: str):
        """Updates progress in DB and notifies subscribers."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(JobModel)
                .where(JobModel.id == job_id)
                .values(
                    progress=progress,
                    current_step=current_step,
                    status="running",
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.commit()

        await self.broadcast_event("job_progress", {
            "job_id": job_id,
            "progress": round(progress, 1),
            "current_step": current_step,
            "status": "running"
        })

    async def _process_loop(self):
        """Main loop that executes tasks strictly one at a time."""
        while self._is_running:
            try:
                task_data = await self._queue.get()
                job_id = task_data["job_id"]
                self._current_job_id = job_id
                func = task_data["func"]
                args = task_data["args"]
                kwargs = task_data["kwargs"]

                logger.info(f"Starting execution of job {job_id} ({task_data['job_type']})")
                await self.update_job_progress(job_id, 0.0, "Starting job...")

                try:
                    # Provide progress updater callback to task if it accepts `progress_cb`
                    kwargs["progress_cb"] = lambda p, s: asyncio.create_task(self.update_job_progress(job_id, p, s))
                    result = await func(*args, **kwargs)

                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(JobModel)
                            .where(JobModel.id == job_id)
                            .values(
                                status="completed",
                                progress=100.0,
                                current_step="Completed successfully",
                                updated_at=datetime.now(timezone.utc)
                            )
                        )
                        await session.commit()

                    await self.broadcast_event("job_completed", {
                        "job_id": job_id,
                        "project_id": task_data["project_id"],
                        "clip_id": task_data["clip_id"],
                        "status": "completed",
                        "progress": 100.0,
                        "current_step": "Completed successfully"
                    })
                    logger.info(f"Job {job_id} completed successfully.")

                except Exception as e:
                    err_msg = str(e)
                    stack = traceback.format_exc()
                    logger.error(f"Job {job_id} failed: {err_msg}\n{stack}")

                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(JobModel)
                            .where(JobModel.id == job_id)
                            .values(
                                status="failed",
                                error=f"{err_msg}\n{stack}",
                                current_step="Failed with error",
                                updated_at=datetime.now(timezone.utc)
                            )
                        )
                        await session.commit()

                    await self.broadcast_event("job_failed", {
                        "job_id": job_id,
                        "project_id": task_data["project_id"],
                        "clip_id": task_data["clip_id"],
                        "status": "failed",
                        "error": err_msg
                    })

                finally:
                    self._current_job_id = None
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue runner: {e}")
                await asyncio.sleep(1)

# Global singleton instance
job_queue = JobQueueManager()
