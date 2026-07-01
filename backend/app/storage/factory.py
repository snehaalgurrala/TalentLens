from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend


def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
    raise NotImplementedError(
        f"Storage backend '{settings.STORAGE_BACKEND}' is not configured. "
        "Supported values: 'local'."
    )
