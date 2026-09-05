from fastapi import APIRouter
from uuid import UUID
from fastapi import HTTPException
from backend.models import JobCreate
from psycopg.errors import UniqueViolation
from backend.db import create_job, find_job, list_all,get_job_by_idempotency_key
from backend.tasks import execute_job
router = APIRouter()

@router.post("/jobs")
def create_jobs(job: JobCreate): # job object sent in
    try:
        created_job = create_job(job.job_type, job.payload, job.idempotency_key)
    except UniqueViolation: # if the key is not unique and gets flagged
        existing_job = get_job_by_idempotency_key(job.idempotency_key)

        if existing_job is not None:
            existing_job_type, existing_payload = existing_job
        elif existing_job is None:
            raise HTTPException(
                status_code=500,
                detail="Idempotency conflict occurred but existing job was not found"
            )

        if job.payload == existing_payload and job.job_type == existing_job_type:
            return existing_job
        else:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used for a different request"
            )
    if created_job is None:
        raise RuntimeError("create_job returned no row")

    execute_job.delay(str(created_job[0]))
    return created_job

@router.get("/jobs/{job_id}")
def get_job(job_id: UUID):
    job = find_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/jobs")
def list_jobs():
    return list_all()

