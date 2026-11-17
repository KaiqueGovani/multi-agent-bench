import re
from pathlib import Path
from uuid import UUID

from app.adapters.storage.base import StoredFile
from app.core.config import get_settings


class LocalStorageAdapter:
    provider = "local"

    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self._base_path = Path(base_path or settings.local_storage_path)

    def save(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        original_filename: str,
        content: bytes,
    ) -> StoredFile:
        safe_filename = self._safe_filename(original_filename)
        relative_path = Path("attachments") / str(conversation_id) / str(message_id) / f"{attachment_id}-{safe_filename}"
        destination = self._base_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredFile(
            storage_key=relative_path.as_posix(),
            provider=self.provider,
            path=destination,
        )

    def read(self, storage_key: str) -> bytes:
        return self.resolve(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self.resolve(storage_key, reject_symlinks=True)
        path.unlink(missing_ok=True)
        base = self._base_path.resolve()
        for directory in path.parents:
            if directory == base:
                break
            try:
                directory.rmdir()
            except OSError:
                break

    def resolve(self, storage_key: str, *, reject_symlinks: bool = False) -> Path:
        relative_path = Path(storage_key)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("Invalid storage key")
        if reject_symlinks:
            candidate = self._base_path
            for part in relative_path.parts:
                candidate = candidate / part
                if candidate.is_symlink():
                    raise ValueError("Invalid storage key")
        path = self._base_path / relative_path
        resolved_base = self._base_path.resolve()
        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(resolved_base):
            raise ValueError("Invalid storage key")
        return resolved_path

    @staticmethod
    def _safe_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
        return cleaned or "attachment"
