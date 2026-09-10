import time

from backend.db import get_connection
from backend.tasks import execute_job


def get_unpublished_event():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, job_id
                FROM outbox_events
                WHERE published = FALSE
                ORDER BY created_at
                LIMIT 1
                """
            )

            return cursor.fetchone()


def mark_outbox_published(event_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE outbox_events
                SET
                    published = TRUE,
                    published_at = NOW()
                WHERE id = %s
                """,
                (event_id,)
            )


def run_dispatcher():
    while True:
        event = get_unpublished_event()

        if event is None:
            time.sleep(1)
            continue

        event_id, job_id = event

        execute_job.delay(str(job_id))
        mark_outbox_published(event_id)


if __name__ == "__main__":
    run_dispatcher()


