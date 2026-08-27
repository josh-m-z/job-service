from fastapi import APIRouter
from uuid import UUID
from fastapi import HTTPException
from backend.models import JobCreate
from backend.db import create_job, find_job, list_all

router = APIRouter()

@router.post("/jobs")
def create_jobs(job: JobCreate):
    return create_job(job.job_type, job.payload)


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID):
    job = find_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/jobs")
def list_jobs():
    return list_all()

