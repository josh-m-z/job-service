import os
import psycopg
from dotenv import load_dotenv

load_dotenv(".env") # loads .env, becomes part of the current python process
database_url = os.getenv("DATABASE_URL") # os checks the .env variables alreayd loaded
print(database_url)

if database_url is None:
    raise RuntimeError("Database URL is not set")

connection = psycopg.connect(database_url) # connection to db server, not just local file

with connection.cursor() as cursor:
    cursor.execute("SELECT id, name FROM test_items")
    print(cursor.fetchall())

connection.commit()
connection.close()
