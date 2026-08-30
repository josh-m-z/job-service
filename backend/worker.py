import time
from uuid import uuid4
from psycopg.types.json import Jsonb
from backend.db import get_connection



def simulate_work(payload):
    seconds = payload["seconds"]

    time.sleep(seconds)
    return { "result": f"Waited {seconds} seconds." }

def sum_numbers(payload):
    total_sum = sum(payload["numbers"])

    return { "result": total_sum }

HANDLERS = {
    "simulate_work": simulate_work,
    "sum_numbers": sum_numbers
    } # full caps this is a constant, doesnt change

def claim_job():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, job_type, payload
                FROM jobs
                WHERE status = %s
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                ("queued", )
            )
            job = cursor.fetchone()

            if job is not None:
                job_id, job_type, payload = job
                print(f"Claimed: {job_id}")
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'running'
                    WHERE id = %s
                    """,
                    (job_id, )
                )
                return job_id, job_type, payload
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
                return attempt_id # return this since we need other functions to edit those attempts when they succeed or fail, we need ot be ableto find the exact attmept row, this is similar to just returning thr attmept row itself since we can find it later.

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



def run_worker():
    while True:
        job = claim_job()
        if job is not None:
            job_id, job_type, payload = job
            try:
                handler = HANDLERS[job_type] # could have keyeerror, thats a job execution fialure
                result = handler(payload)
            except Exception as error:
                log_failure(job_id, str(error))
                continue
 implements this,
            log_success(job_id, Jsonb(result))

        else:
            time.sleep(1) # waits for a queued status to exists

if __name__ == "__main__":
    run_worker()




