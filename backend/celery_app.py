from celery import Celery

celery_app = Celery(
    "job-service",
    broker="redis://localhost:6379/0",
    include=["backend.tasks"]
) # Celery(name, broker's port )

