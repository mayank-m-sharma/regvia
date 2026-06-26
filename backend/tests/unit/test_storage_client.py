"""Unit tests for StorageClient — boto3 is mocked, no network."""

from unittest.mock import MagicMock

import pytest

from app.storage.client import StorageClient


@pytest.fixture()
def mock_s3(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr("app.storage.client._make_s3_client", lambda: mock)
    return mock


@pytest.mark.asyncio
async def test_upload_calls_put_object(mock_s3: MagicMock) -> None:
    client = StorageClient()
    client._client = mock_s3
    await client.upload("documents/test.pdf", b"data", "application/pdf")
    mock_s3.put_object.assert_called_once_with(
        Bucket=client._bucket,
        Key="documents/test.pdf",
        Body=b"data",
        ContentType="application/pdf",
    )


@pytest.mark.asyncio
async def test_get_presigned_download_url_returns_string(mock_s3: MagicMock) -> None:
    mock_s3.generate_presigned_url.return_value = "https://example.com/presigned"
    client = StorageClient()
    client._client = mock_s3
    url = await client.get_presigned_download_url("documents/test.pdf")
    assert url == "https://example.com/presigned"
    mock_s3.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": client._bucket, "Key": "documents/test.pdf"},
        ExpiresIn=3600,
    )


@pytest.mark.asyncio
async def test_delete_calls_delete_object(mock_s3: MagicMock) -> None:
    client = StorageClient()
    client._client = mock_s3
    await client.delete("documents/test.pdf")
    mock_s3.delete_object.assert_called_once_with(
        Bucket=client._bucket, Key="documents/test.pdf"
    )
