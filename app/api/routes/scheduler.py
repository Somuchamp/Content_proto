from fastapi import APIRouter, HTTPException
from app.models.schemas import SchedulerRequest, SchedulerResponse, RefreshInterval
from app.services.scheduler_service import (
    add_refresh_job, cancel_refresh_job, list_jobs
)
from app.storage.file_storage import load_content_json

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


@router.post("/set", response_model=SchedulerResponse)
async def set_refresh(req: SchedulerRequest):
    """Set or update the auto-refresh schedule for an existing content item."""
    record = load_content_json(req.content_id)
    if not record:
        raise HTTPException(status_code=404, detail="Content not found")

    from app.api.routes.content import _run_full_pipeline

    async def refresh_job(cid: str):
        rec = load_content_json(cid)
        if rec:
            await _run_full_pipeline(
                name=rec["name"],
                content_type=rec["content_type"],
                country=rec["country"],
                max_headings=rec.get("metadata", {}).get("total_headings", 7),
                refresh_interval=RefreshInterval(req.refresh_interval),
                custom_interval_hours=req.custom_interval_hours,
                content_id=cid,
            )

    job_info = add_refresh_job(
        content_id=req.content_id,
        interval=req.refresh_interval,
        custom_hours=req.custom_interval_hours,
        refresh_fn=refresh_job,
    )

    return SchedulerResponse(
        job_id=job_info["job_id"],
        content_id=req.content_id,
        next_run_at=job_info["next_run_at"],
        message=f"Refresh scheduled: {req.refresh_interval.value} "
                f"(every {job_info['interval_hours']}h).",
    )


@router.delete("/cancel/{content_id}")
async def cancel_schedule(content_id: str):
    """Cancel the auto-refresh schedule for a content item."""
    if not cancel_refresh_job(content_id):
        raise HTTPException(
            status_code=404,
            detail=f"No active refresh job found for '{content_id}'"
        )
    return {"message": f"Refresh job for '{content_id}' cancelled."}


@router.get("/jobs")
async def get_jobs():
    """List all currently scheduled refresh jobs."""
    return {"jobs": list_jobs()}