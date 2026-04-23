from app.adapters.storage.base import StorageAdapter, StoredFile
from app.adapters.storage.local import LocalStorageAdapter
from app.adapters.storage.s3 import S3CompatibleStorageAdapter
from app.core.config import get_settings


def get_storage_adapter() -> StorageAdapter:
    settings = get_settings()
    if settings.storage_provider == "local":
        return LocalStorageAdapter()
    if settings.storage_provider in {"minio", "s3"}:
        adapter = S3CompatibleStorageAdapter()
        adapter.provider = settings.storage_provider
        return adapter
    raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")


__all__ = [
    "LocalStorageAdapter",
    "S3CompatibleStorageAdapter",
    "StorageAdapter",
    "StoredFile",
    "get_storage_adapter",
]
