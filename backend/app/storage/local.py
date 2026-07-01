import asyncio
from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem under base_path.

    Suitable for development. Swap for an S3/MinIO backend in production
    by implementing StorageBackend and updating the factory.
    """

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    async def save(self, relative_path: str, data: bytes) -> str:
        target = self._base / relative_path
        await asyncio.to_thread(self._write, target, data)
        return relative_path

    async def delete(self, storage_path: str) -> None:
        target = self._base / storage_path
        await asyncio.to_thread(self._unlink, target)

    # ── sync helpers (run inside to_thread) ──────────────────────────────────

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    @staticmethod
    def _unlink(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
