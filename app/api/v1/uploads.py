from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_passenger
from app.models.complaint import ComplaintMedia, MediaType
from app.models.user import User
from app.services.storage_service import storage_service
router = APIRouter(prefix="/uploads", tags=["Uploads"])
def determine_media_type(content_type: str) -> MediaType:
    if content_type.startswith("image/"): return MediaType.image
    if content_type.startswith("video/"): return MediaType.video
    if content_type.startswith("audio/"): return MediaType.audio
    raise HTTPException(415, "Unsupported file type")
@router.post("", status_code=201)
async def upload(file: UploadFile = File(...), language: str | None = Form(None), db: Session = Depends(get_db), _: User = Depends(require_passenger)):
    settings = get_settings()
    if not file.filename or not Path(file.filename).suffix or file.content_type not in settings.allowed_types: raise HTTPException(415, "Unsupported file type")
    media_type = determine_media_type(file.content_type)
    url, size = await storage_service.upload(file)
    if size == 0:
        await storage_service.delete(url); raise HTTPException(422, "File cannot be empty")
    if size > settings.max_upload_size_mb * 1024 * 1024:
        await storage_service.delete(url); raise HTTPException(413, "File exceeds maximum upload size")
    media = ComplaintMedia(media_type=media_type, original_url=url, file_name=file.filename, file_size=size, mime_type=file.content_type)
    db.add(media); db.commit(); db.refresh(media)
    return {"media_id": media.id, "media_type": media.media_type, "file_name": media.file_name, "file_size": media.file_size, "url": media.original_url, "language": language}
