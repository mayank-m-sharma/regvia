"""Unit tests for Celery task dispatch."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Task-level tests (synchronous — Celery tasks are sync wrappers)
# ---------------------------------------------------------------------------


def test_process_document_task_max_retries_is_3() -> None:
    """Task is configured to retry at most 3 times."""
    from app.worker.tasks import process_document_task

    assert process_document_task.max_retries == 3


def test_process_document_task_calls_asyncio_run() -> None:
    """Task passes a coroutine from process_document to asyncio.run."""
    doc_id = str(uuid.uuid4())

    with patch("app.worker.tasks.asyncio.run") as mock_run:
        from app.worker.tasks import process_document_task

        process_document_task.apply(args=[doc_id])

    mock_run.assert_called_once()


def test_process_document_task_retries_exhausted_are_handled() -> None:
    """MaxRetriesExceededError is caught after all retries — task does not re-raise."""
    doc_id = str(uuid.uuid4())

    with patch(
        "app.worker.tasks.asyncio.run",
        side_effect=RuntimeError("connection refused"),
    ):
        from app.worker.tasks import process_document_task

        # Should NOT propagate — MaxRetriesExceededError is caught internally
        process_document_task.apply(args=[doc_id])


def test_celery_app_broker_uses_redis_url() -> None:
    """Celery app broker is set to settings.REDIS_URL."""
    from app.core.settings import settings
    from app.worker.celery_app import celery_app

    assert settings.REDIS_URL in celery_app.conf.broker_url


# ---------------------------------------------------------------------------
# Feature-flag dispatch logic
# ---------------------------------------------------------------------------


def test_use_celery_default_is_false() -> None:
    """USE_CELERY defaults to False — BackgroundTasks path is the default."""
    from app.core.settings import Settings

    s = Settings()
    assert s.USE_CELERY is False


def test_use_celery_can_be_enabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """USE_CELERY=true env var enables Celery path."""
    monkeypatch.setenv("USE_CELERY", "true")
    from importlib import reload

    import app.core.settings as settings_module

    reload(settings_module)
    assert settings_module.Settings().USE_CELERY is True

    reload(settings_module)  # restore default


def test_process_document_task_is_registered() -> None:
    """Task is registered in Celery app under expected name."""
    from app.worker.celery_app import celery_app

    assert "regvia.process_document" in celery_app.tasks


def test_process_document_task_acks_late() -> None:
    """Task uses acks_late so it is requeued if the worker dies mid-processing."""
    from app.worker.tasks import process_document_task

    assert process_document_task.acks_late is True
