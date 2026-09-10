from fastapi import APIRouter, UploadFile, File
from uuid import UUID
from fastapi import HTTPException
from backend.models import JobCreate
from psycopg.errors import UniqueViolation
from backend.db import (
    create_job,
    find_job,
    list_all,
    get_job_by_idempotency_key,
    cancel_job,
    insert_document,
    delete_document,
    get_document_result)

from uuid import uuid4
from pathlib import Path


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

  # execute_job.delay(str(created_job[0]))
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

@router.get("/jobs/{job_id}/cancel")
def cancel_jobs(job_id: UUID):
    job = find_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job[3] != "queued":
        raise HTTPException(
            status_code=409,
            detail="Only queued jobs can be cancelled."
        )
    cancel_job(job_id)

    return {"status": "cancelled"}

"""
File(...) means required File(), with the ..., the parameter must come from uplaoded file in the http re, acces to file.filename
file.content_type
await file.read()
"""
# ------------------
# Document Section
# ------------------
@router.post("/documents") # adds and processes a document, uses the job post fucntion
async def create_documents(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only " \
            "PDF files are supported"
        )
    document_id = uuid4()

    UPLOAD_DIR = Path("uploads") # uppercase bc constant
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_path = UPLOAD_DIR / f"{document_id}.pdf" # the / here means join paths, like uploads/abc.pdf. This makes the file path linked to the uploads dir

    contents = await file.read() # reads the file beign sent http req

    try:
        # write to uplaods, keeps the file's bytes on hand
        with open(file_path, "wb") as f:
            f.write(contents) # .write could fail

            document = insert_document(document_id, file.filename, file.content_type, file_path)

            job = create_job(
            job_type="process_document",
            payload={"document_id": str(document_id)},
            idempotency_key=None,
            )

            return document
    except: # acocount for any fiaure, delete any insertion or uplaod to ensure no leftovers
        delete_document(document_id)
        file_path.unlink(missing_ok=True)
        raise

@router.get("/documents/{document_id}/result")
def read_document_result(document_id: UUID):
    result = get_document_result(document_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Document result not found"
        )

    return result # reuslts comes for mthe doc reusls table, not the jobs executions, this is more direct and makes more sense 
