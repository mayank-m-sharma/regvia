"""Celery tasks for document processing."""

from __future__ import annotations

import asyncio

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger

from app.worker.celery_app import celery_app

logger = get_task_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = 60  # seconds; doubles each retry (60 → 120 → 240)


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="regvia.process_document",
    max_retries=_MAX_RETRIES,
    default_retry_delay=_RETRY_BACKOFF,
    acks_late=True,
)
def process_document_task(self: Task, document_id: str) -> None:
    """Durable document processing task.

    Runs the async pipeline synchronously via asyncio.run().
    Retries up to 3 times with exponential backoff on failure.
    After max retries, document status is set to `failed`.
    """
    from app.services.processing import (
        process_document,  # local import — avoids circular
    )

    try:
        asyncio.run(process_document(document_id))
    except MaxRetriesExceededError:
        logger.error(
            "process_document max retries exceeded | document_id=%s", document_id
        )
    except Exception as exc:
        logger.warning(
            "process_document failed, retrying | document_id=%s attempt=%d",
            document_id,
            self.request.retries + 1,
        )
        countdown = _RETRY_BACKOFF * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc
