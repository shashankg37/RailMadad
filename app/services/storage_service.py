from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class LocalStorageService:
    """Development storage adapter. Replace behind this interface for Cloudinary."""

    async def upload(self, file: UploadFile) -> tuple[str, int]:
        settings = get_settings()
        settings.local_storage_path.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "upload").suffix
        name = f"{uuid4()}{suffix}"
        destination = settings.local_storage_path / name
        size = 0
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                target.write(chunk)
        return f"/media/{name}", size

    async def delete(self, url: str) -> None:
        path = get_settings().local_storage_path / Path(url).name
        if path.exists():
            path.unlink()


class CloudinaryStorageService:
    async def upload(self, file: UploadFile) -> tuple[str, int]:
        settings = get_settings()
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError as exc:
            raise RuntimeError("cloudinary is not installed") from exc

        config = {
            "cloud_name": settings.cloudinary_cloud_name,
            "api_key": settings.cloudinary_api_key,
            "api_secret": settings.cloudinary_api_secret,
            "secure": True,
        }
        cloudinary.config(**config)

        file_content = await file.read()
        upload = cloudinary.uploader.upload(file_content, resource_type="auto")
        url = str(upload.get("secure_url") or upload.get("url") or "")
        size = int(upload.get("bytes") or len(file_content))
        return url, size

    async def delete(self, url: str) -> None:
        if not url:
            return
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError:
            return
        cloudinary.uploader.destroy(url.split("/")[-1].split(".")[0], resource_type="auto")


class StorageService:
    def __init__(self):
        self._fallback = LocalStorageService()
        self._cloudinary = CloudinaryStorageService()

    async def upload(self, file: UploadFile) -> tuple[str, int]:
        settings = get_settings()
        if settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret:
            try:
                return await self._cloudinary.upload(file)
            except Exception:
                return await self._fallback.upload(file)
        return await self._fallback.upload(file)

    async def delete(self, url: str) -> None:
        settings = get_settings()
        if settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret:
            try:
                await self._cloudinary.delete(url)
                return
            except Exception:
                pass
        await self._fallback.delete(url)


storage_service = StorageService()
