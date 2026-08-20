from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.complaint import ComplaintStatus, MediaType
class CreateComplaintRequest(BaseModel):
    media_ids: list[str] = Field(min_length=1, max_length=10)
    language: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$")
class AnalysisResult(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    subcategory: str = Field(min_length=1, max_length=120)
    severity: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1, max_length=4000)
    suggested_action: str = Field(min_length=1, max_length=4000)
    coach_number: str | None = Field(None, max_length=30)
    confidence: float = Field(ge=0, le=1)
class StatusUpdate(BaseModel):
    status: ComplaintStatus
    resolution_note: str | None = Field(None, max_length=4000)
class MediaResponse(BaseModel):
    id: str; media_type: MediaType; original_url: str; annotated_url: str | None; file_name: str; file_size: int; mime_type: str; created_at: datetime
    model_config = {"from_attributes": True}
class ComplaintResponse(BaseModel):
    complaint_id: str; language: str; media_type: MediaType; category: str | None; subcategory: str | None; severity: int | None; summary: str | None; suggested_action: str | None; coach_number: str | None; confidence: float | None; department: str | None; status: ComplaintStatus; created_at: datetime; updated_at: datetime; resolved_at: datetime | None; resolution_note: str | None; media: list[MediaResponse]
    model_config = {"from_attributes": True}
class ComplaintCreated(BaseModel): complaint_id: str; status: ComplaintStatus; created_at: datetime
class ComplaintPage(BaseModel): items: list[ComplaintResponse]; page: int; limit: int; total: int; pages: int
