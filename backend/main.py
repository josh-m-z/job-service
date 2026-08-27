from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.routes.jobs import router
from backend.db import initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app...")
    initialize_database() # make sure the db is up and created at least once

    yield

    print("Shutting app down...")


app = FastAPI(lifespan=lifespan)

app.include_router(router)


