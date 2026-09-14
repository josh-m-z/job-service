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
    outbox_event_id = uuid4()
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

            created_job = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO outbox_events (id, job_id)
                VALUES (%s, %s)
                """,
                (outbox_event_id, job_id, )
            )
            # new syntax, RETURNING ... ensures that these things are returned

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
def cancel_job(job_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'failed'
                WHERE id = %s
                  AND status = 'queued'
                RETURNING id
                """,
                (job_id,)
            ) # think of when it's approp to return somethign from the sql, here we see it turns noen if not foundl which is ideal and id if found

            return cursor.fetchone()

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


# --------------------
# Document Section
# --------------------
def insert_document(document_id, filename, content_type, file_path, batch_id=None):
    with get_connection() as connecton:
        with connecton.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (id, filename, content_type, file_path, batch_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (document_id, filename, content_type, str(file_path), batch_id)
            ) # RETURNING * returns all cols of the row, inclduing ones we didnt write in liek created_at

            return cursor.fetchone()


def delete_document(document_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM documents
                WHERE id = %s;
                """,
                (document_id,)
            )

def get_document(document_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, content_type, file_path, created_at
                FROM documents
                WHERE id = %s;
                """,
                (document_id,)
            )

            return cursor.fetchone()

def save_document_result(
    document_id,
    text,
    page_count,
    word_count,
    character_count,
    extracted_data
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO document_results (
                    document_id,
                    text,
                    page_count,
                    word_count,
                    character_count,
                    extracted_data
                )
                VALUES (%s, %s, %s, %s, %s, %s)

                ON CONFLICT (document_id)
                DO UPDATE SET
                    text = EXCLUDED.text,
                    page_count = EXCLUDED.page_count,
                    word_count = EXCLUDED.word_count,
                    character_count = EXCLUDED.character_count,
                    processed_at = NOW(),
                    extracted_data = EXCLUDED.extracted_data;
                """,
                (
                    document_id,
                    text,
                    page_count,
                    word_count,
                    character_count,
                    Jsonb(extracted_data)
                )
            )

def get_document_result(document_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT document_id, text, page_count,
                       word_count, character_count, processed_at
                FROM document_results
                WHERE document_id = %s;
                """,
                (document_id,)
            )

            return cursor.fetchone()

# Batches
# just needs to store a uuid, since the documets are linked together by this id
def insert_batch(batch_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO batches (id)
                VALUES (%s)
                RETURNING *;
                """,
                (batch_id,)
            )

            return cursor.fetchone()



def get_batch_documents(batch_id):

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    d.id,
                    d.filename,
                    j.status,
                    j.attempt_count,
                    j.last_error
                FROM documents d
                LEFT JOIN jobs j
                    ON j.job_type = 'process_document'
                    AND j.payload->>'document_id' = d.id::text
                WHERE d.batch_id = %s;
                """,
                (batch_id,)
            )

            return cursor.fetchall()
