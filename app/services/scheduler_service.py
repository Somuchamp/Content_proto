from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from app.models.schemas import RefreshInterval
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

INTERVAL_HOURS = {
    RefreshInterval.daily:   24,
    RefreshInterval.weekly:  168,
    RefreshInterval.monthly: 720,
}

scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()


def _resolve_hours(interval: RefreshInterval, custom_hours: int | None) -> int:
    if interval == RefreshInterval.custom:
        return custom_hours or 24
    return INTERVAL_HOURS.get(interval, 168)


def add_refresh_job(
    content_id: str,
    interval: RefreshInterval,
    custom_hours: int | None,
    refresh_fn,
) -> dict:
    """
    Step 7 — Scheduled Refresh:
    Registers a periodic job to re-collect, re-process, and regenerate content.
    """
    job_id = f"refresh_{content_id}"
    hours = _resolve_hours(interval, custom_hours)

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        refresh_fn,
        trigger="interval",
        hours=hours,
        id=job_id,
        args=[content_id],
        replace_existing=True,
    )

    next_run = datetime.now() + timedelta(hours=hours)
    logger.info(f"Scheduled '{job_id}' every {hours}h. Next: {next_run}")
    return {"job_id": job_id, "next_run_at": next_run, "interval_hours": hours}


def cancel_refresh_job(content_id: str) -> bool:
    job_id = f"refresh_{content_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled job '{job_id}'")
        return True
    return False


def list_jobs() -> list[dict]:
    return [
        {"job_id": job.id, "next_run_at": job.next_run_time}
        for job in scheduler.get_jobs()
    ]