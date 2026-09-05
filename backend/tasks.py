from psycopg.types.json import Jsonb

from backend.celery_app import celery_app
from backend.db import get_connection

from backend.worker import (
    HANDLERS,
    start_attempt,
    finish_attempt_success,
    finish_attempt_failure,
    log_success,
    log_failure,
    requeue_job
)

@celery_app.task(bind=True, max_retries=None) # passes taks context into first paramter
def execute_job(self, job_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT job_type, payload, max_attempts, attempt_count
                FROM jobs
                WHERE id = %s
                """,
                (job_id,)
            )

            job = cursor.fetchone()

            if job is None:
                raise ValueError("Job not found.")

            job_type, payload, max_attempts, attempt_count = job

            cursor.execute(
                """
                UPDATE jobs
                SET status = 'running'
                WHERE id = %s
                """,
                (job_id,)
            )

    attempt_id, attempt_count = start_attempt(job_id)

    try:
        handler = HANDLERS[job_type]

        if job_type == "fail_then_succeed":
            result = handler(payload, attempt_count)
        else:
            result = handler(payload)
    except Exception as error:
        print("ENTERED RETRY BRANCH")
        finish_attempt_failure(attempt_id, str(error))
        if attempt_count < max_attempts:
            requeue_job(job_id, str(error))

            raise self.retry(
                exc=error,
                countdown=5
            )
        else:
            log_failure(job_id, str(error))

    else:
        finish_attempt_success(attempt_id)
        log_success(job_id, Jsonb(result))


