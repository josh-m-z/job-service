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
    get_document_result,
    insert_batch,
    get_batch_documents)

from uuid import uuid4
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("uploads") # uppercase bc constant
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

@router.post("/batches")
async def create_batch(files: list[UploadFile] = File(...)):
    # checks if the files are all pdfs
    accepted = []
    rejected = []
    batch_id = uuid4()
    batch = insert_batch(batch_id)

    # rejected list if not pdf
    for file in files:
        if file.content_type != "application/pdf":
            rejected.append({
                "file_name": file.filename,
                "error": "File must be a PDF"
            })
            continue

        try:
            document_id = uuid4()
            file_path = UPLOAD_DIR / f"{document_id}.pdf"

            contents = await file.read()

            with open(file_path, "wb") as f:
                f.write(contents)

            document = insert_document(
                document_id,
                file.filename,
                file.content_type,
                file_path,
                batch_id
            )

            job = create_job(
                "process_document",
                {"document_id": str(document_id)},
                idempotency_key=None
            )

            accepted.append({
                "document": document,
                "job": job
            })

        except Exception as error:
            # at this point, files have been written so must delete them and unlink and append to rejected
            delete_document(document_id)
            file_path.unlink(missing_ok=True)
            rejected.append({
                "file_name": file.filename,
                "error": str(error)
            })


    # batch is ust a uuid and created, but by returning it like this they are grouped, and hte documents share the bath id
    return {
    "batch": batch,
    "accepted": accepted,
    "rejected": rejected
}

@router.get("/batches/{batch_id}")

def get_batch_status(batch_id: UUID):
    documents = get_batch_documents(batch_id)
    queued = 0
    running = 0
    succeeded = 0
    failed = 0
    batch_status = "processing"

    document_list = []

    for document in documents:

        document_id, filename, status, attempt_count, last_error = document

        if status == "queued":
            queued += 1
        elif status == "running":
            running += 1
        elif status == "succeeded":
            succeeded += 1
        elif status == "failed":
            failed += 1

        document_list.append({

            "document_id": document_id,
            "filename": filename,
            "status": status,
            "attempt_count": attempt_count,
            "last_error": last_error
        })

    # after adding all the statuses of the curent state, then reort the overal branch state by checking if there are queued, or running, and if not, then if there are fialed explcilty mention thati t completed but with fiaures
    if queued > 0 or running > 0:
        batch_status = "processing"
    elif failed > 0:
        batch_status = "completed_with_failures"
    else:
        batch_status = "completed"

    return {
        "batch_id": batch_id,
        "total": len(documents),
        "queued": queued,
        "running": running,
        "succeeded": succeeded,
        "failed": failed,
        "documents": document_list,
        "status": batch_status

    }
