from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, relative_path: str, data: bytes) -> str:
        """Persist data at relative_path; return the canonical storage_path."""

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Remove the stored file. Must be a no-op if the file is absent."""
