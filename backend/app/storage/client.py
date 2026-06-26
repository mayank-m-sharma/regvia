import asyncio
from typing import Any

import boto3
from botocore.config import Config

from app.core.settings import settings


def _make_s3_client() -> Any:  # noqa: ANN401
    kwargs: dict[str, Any] = {
        "region_name": settings.AWS_REGION,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID or None,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY or None,
        "config": Config(signature_version="s3v4"),
    }
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


class StorageClient:
    def __init__(self) -> None:
        self._client = _make_s3_client()
        self._bucket = settings.S3_BUCKET_NAME

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get_presigned_upload_url(self, key: str, expires_in: int = 3600) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def get_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )

    async def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist. Used on startup for MinIO local dev."""

        def _create() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except Exception:
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(_create)


storage_client = StorageClient()
