import re
from uuid import UUID

from app.adapters.storage.base import StoredFile
from app.core.config import get_settings


class S3CompatibleStorageAdapter:
    provider = "s3"

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.storage_bucket
        self._client = self._create_client(settings)

    def save(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        original_filename: str,
        content: bytes,
    ) -> StoredFile:
        object_key = (
            f"attachments/{conversation_id}/{message_id}/"
            f"{attachment_id}-{self._safe_filename(original_filename)}"
        )
        self._client.put_object(Bucket=self._bucket, Key=object_key, Body=content)
        return StoredFile(
            storage_key=object_key,
            provider=self.provider,
            bucket=self._bucket,
        )

    def read(self, storage_key: str) -> bytes:
        if storage_key.startswith("/") or ".." in storage_key.split("/"):
            raise ValueError("Invalid storage key")
        response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return response["Body"].read()

    @staticmethod
    def _create_client(settings):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required when STORAGE_PROVIDER is set to minio or s3"
            ) from exc

        return boto3.client(
            "s3",
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            endpoint_url=settings.storage_endpoint_url or None,
            region_name=settings.storage_region,
            config=Config(s3={"addressing_style": settings.storage_addressing_style}),
        )

    @staticmethod
    def _safe_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
        return cleaned or "attachment"
