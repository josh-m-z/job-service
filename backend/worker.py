import time
from uuid import uuid4
from psycopg.types.json import Jsonb
from backend.db import get_connection
from backend.document_processor import process_document

# id made before any loops so that the id stays the same, used to track the worker
WORKER_ID = uuid4()

def simulate_work(payload):
    seconds = payload["seconds"]
    time.sleep(seconds)
    return { "result": f"Waited {seconds} seconds." }

def sum_numbers(payload):
    total_sum = sum(payload["numbers"])
    return { "result": total_sum }

def fail_tester(payload, attempt_count):
     fail_first_n = payload["fail_first_n"]
     if attempt_count <= fail_first_n:
        raise RuntimeError( f"Intentional failure at attempt {attempt_count}")
     return {"result": "Succeeded"}

HANDLERS = {
    "simulate_work": simulate_work,
    "sum_numbers": sum_numbers,
    "fail_then_succeed": fail_tester,
    "process_document": process_document
    } # full caps this is a constant, doesnt change


def recover_stale_job(cursor, job):
    job_id, job_type, payload, max_attempts, attempt_count = job

    # just get attempt id for managing the old attempts and new
    cursor.execute(
        """
        SELECT id
        FROM job_attempts
        WHERE job_id = %s
        AND status = 'running'
        ORDER BY attempt_number DESC
        LIMIT 1
        """,
        (job_id,)
    )
    attempt = cursor.fetchone()

    if attempt is None:
        raise ValueError("Inaccessible attempt id")

    attempt_id = attempt[0]

    # finish old attempt
    cursor.execute(
        """
        UPDATE job_attempts
        SET status = 'failed',
            finished_at = NOW(),
            error = %s
        WHERE id = %s
        """,
        ('Lease expired.', attempt_id)
    )

    if attempt_count < max_attempts:
        # reclaim the job under new worker after failing old attempt
        cursor.execute(
            """
            UPDATE jobs
            SET worker_id = %s, lease_expires_at = NOW() + INTERVAL '2 minutes'
            WHERE id = %s
            """,
            (WORKER_ID, job_id)
        )
        return job_id, job_type, payload, max_attempts, attempt_count

    elif attempt_count >= max_attempts:
        # no need to return since this is essentially ending a job that reached max attempts
        cursor.execute(
            """
            UPDATE jobs
            SET status = 'failed', last_error = %s, result = %s
            WHERE id = %s
            """,
            ('Lease expired.', None, job_id)
        )
        return None
def mark_interrupted_attempt(job_id):
    with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE job_attempts
                    SET
                        status = 'failed',
                        finished_at = NOW(),
                        error = 'Worker lost during execution'
                    WHERE job_id = %s AND status = 'running'
                    """,
                    (job_id, )
                )

def claim_job():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, job_type, payload, status, max_attempts, attempt_count
                FROM jobs
                WHERE (status = %s AND attempt_count < max_attempts) OR (status = %s AND lease_expires_at < NOW())
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                ("queued", "running" )
            ) # anything seen running from here is expired as well due to the check inside here
            job = cursor.fetchone()

            if job is not None:
                job_id, job_type, payload, status, max_attempts, attempt_count = job

                if status == 'queued':
                    print(f"Claimed: {job_id}")
                    cursor.execute(
                        """
                        UPDATE jobs
                        SET status = 'running', worker_id = %s, lease_expires_at = NOW() + INTERVAL '2 minutes'
                        WHERE id = %s
                        """,
                        (WORKER_ID, job_id)
                    )
                    return job_id, job_type, payload, max_attempts, attempt_count

                elif status == 'running':
                    return recover_stale_job(cursor, job)

            return None

def start_attempt(job_id):
    with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET attempt_count = attempt_count + 1
                    WHERE id = %s
                    RETURNING attempt_count
                    """,
                    (job_id,)
                )
                row = cursor.fetchone()

                if row is None:
                    raise ValueError("Job not found.")

                attempt_id = uuid4()
                attempt_count = row[0] # ow has been checked ot not have none
                cursor.execute(
                    """
                    INSERT INTO job_attempts ( id, job_id, attempt_number)
                    Values (%s, %s, %s)
                    """,
                    (attempt_id, job_id, attempt_count)
                )
                return attempt_id, attempt_count # return this since we need other functions to edit those attempts when they succeed or fail, we need ot be ableto find the exact attmept row, this is similar to just returning thr attmept row itself since we can find it later.

def finish_attempt_success(attempt_id):
    with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE job_attempts
                        SET status = 'succeeded',
                        finished_at = NOW()
                        WHERE id = %s
                        """,
                        (attempt_id,)
                    )

def finish_attempt_failure(attempt_id, error):
    with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE job_attempts
                        SET status = 'failed',
                            finished_at = NOW(),
                            error = %s
                        WHERE id = %s
                        """,
                        (error, attempt_id)
                    )

def log_success(job_id, result):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                Update jobs
                SET status = %s, result = %s, last_error = %s
                WHERE id = %s
                """,
                ("succeeded", result, None, job_id)
            )

def log_failure(job_id, failure):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                Update jobs
                SET status = %s, last_error = %s, result = %s
                WHERE id = %s
                """,
                ("failed", failure, None, job_id)
            )

def requeue_job(job_id, error):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'queued', last_error = %s
                WHERE id = %s AND status = 'running'
                """,
                (error, job_id)
            ) # lasT_error must be preserved

def run_worker():
    while True:
        job = claim_job()

        if job is not None:
            job_id, job_type, payload, max_attempts, attempt_count = job

            if attempt_count < max_attempts:
                attempt_id, attempt_count = start_attempt(job_id)
                try:
                    handler = HANDLERS[job_type] # could have keyeerror, thats a job execution fialure
                    if job_type == "fail_then_succeed":
                        result = handler(payload, attempt_count)
                    else:
                        result = handler(payload)
                except Exception as error:
                    finish_attempt_failure(attempt_id, str(error)) # happens no matter what, invariant
                    if attempt_count >= max_attempts:
                        log_failure(job_id, str(error))
                    else:
                        requeue_job(job_id, str(error))
                    continue
                else:
                    finish_attempt_success(attempt_id)
                    log_success(job_id, Jsonb(result))

        else:
            time.sleep(1) # waits for a queued status to exists*

if __name__ == "__main__":
    run_worker()
