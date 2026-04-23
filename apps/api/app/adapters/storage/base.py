from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    provider: str
    bucket: str | None = None
    path: Path | None = None


class StorageAdapter(Protocol):
    provider: str

    def save(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        original_filename: str,
        content: bytes,
    ) -> StoredFile:
        ...

    def read(self, storage_key: str) -> bytes:
        ...
