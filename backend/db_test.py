import os
import psycopg
from pathlib import Path
from dotenv import load_dotenv
from typing import LiteralString, cast
from uuid import uuid4
from psycopg.types.json import Jsonb

load_dotenv(".env") # loads .env, becomes part of the current python process
database_url = os.getenv("DATABASE_URL") # os checks the .env variables alreayd loaded
schema = Path("backend/schema.sql").read_text() # Make path object to sql schema, then read it and put it in as string type using .read_text() in schema, execute after
schema = cast(LiteralString, schema) # make schema string read as literal by pylance (essential the same as if schema were direct quaotions, str could be a varibale, Literal is quotes)




if database_url is None:
    raise RuntimeError("Database URL is not set")

connection = psycopg.connect(database_url) # connection to db server, not just local file

job_id = uuid4()
job_type = "simulate_work"
payload = {"seconds": 5}
status = "queued"

with connection.cursor() as cursor: # cursor is like active convo, sends and returns

    cursor.execute(
        """
        INSERT INTO jobs (id, job_type, payload, status)
        VALUES (%s, %s, %s, %s)
        """,
        (job_id, job_type, Jsonb(payload), status)
    )

    cursor.execute(
        """
        SELECT id, job_type, payload, status
        FROM jobs
        ORDER BY created_at DESC
        """
    )
    print(cursor.fetchall())

connection.commit()
connection.close()
