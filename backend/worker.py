import time
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
                LIMIT 1
                """,
                ("queued", )
            )
            job = cursor.fetchone()

            if job is not None:
                job_id, job_type, payload = job
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

            log_success(job_id, Jsonb(result))

        else:
            time.sleep(1) # waits for a queued status to exists

if __name__ == "__main__":
    run_worker()




