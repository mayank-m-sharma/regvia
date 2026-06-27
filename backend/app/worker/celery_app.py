"""Celery application factory."""

from celery import Celery

from app.core.settings import settings

celery_app = Celery(
    "regvia",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # task acknowledged after completion, not on receipt
    task_reject_on_worker_lost=True,  # re-queue if worker dies mid-task
    task_track_started=True,
)
