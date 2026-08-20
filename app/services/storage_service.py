from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from app.core.config import get_settings

class LocalStorageService:
    """Development storage adapter. Replace behind this interface for Cloudinary."""
    async def upload(self, file: UploadFile) -> tuple[str, int]:
        settings = get_settings(); settings.local_storage_path.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "upload").suffix
        name = f"{uuid4()}{suffix}"; destination = settings.local_storage_path / name
        size = 0
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024): size += len(chunk); target.write(chunk)
        return f"/media/{name}", size
    async def delete(self, url: str) -> None:
        path = get_settings().local_storage_path / Path(url).name
        if path.exists(): path.unlink()
storage_service = LocalStorageService()
