import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
from typing import cast, LiteralString
from psycopg.types.json import Jsonb
from uuid import uuid4

schema = Path(__file__).with_name("schema.sql").read_text()
load_dotenv(".env")

database_url = os.getenv("DATABASE_URL")


def get_connection():
    if database_url is None:
        raise RuntimeError("DATABASE_URL is not set")

    return psycopg.connect(database_url)

def initialize_database():
    connection = get_connection()

    with connection.cursor() as cursor:

        cursor.execute(cast(LiteralString, schema))

    connection.commit()
    connection.close()

def create_job(job_type, payload, idempotency_key=None):
    job_id = uuid4()
    # Context manager on normal exit does the commit + close, on excpeton it does it as well
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jobs (id, job_type, payload, status, idempotency_key)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, job_type, payload, status, created_at, idempotency_key;
                """,
                (job_id, job_type, Jsonb(payload), "queued", idempotency_key)
            )
            # new syntax, RETURNING ... ensures that these things are returned
            created_job = cursor.fetchone()
            return created_job

def find_job(job_id):
    with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, job_type, payload, status, created_at
                    FROM jobs
                    WHERE id = %s
                    """,
                    (job_id, )
                )

                job = cursor.fetchone()

                return job

def get_job_by_idempotency_key(idempotency_key):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT job_type, payload
                FROM jobs
                WHERE idempotency_key = %s
                """,
                (idempotency_key, )
                )

            job = cursor.fetchone()
            return job

def list_all():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, job_type, payload, status, created_at, result, last_error
                FROM jobs
                """
            )

            jobs = cursor.fetchall()
            return jobs


