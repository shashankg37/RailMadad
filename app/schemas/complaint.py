from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.models.complaint import ComplaintStatus, MediaType
class CreateComplaintRequest(BaseModel):
    media_ids: list[str] = Field(default_factory=list, max_length=10)
    language: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$")
    text: str | None = Field(None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_evidence(self):
        if not self.media_ids and not self.text:
            raise ValueError("At least one media item or text is required")
        return self
class AnalysisResult(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    subcategory: str = Field(min_length=1, max_length=120)
    severity: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1, max_length=4000)
    suggested_action: str = Field(min_length=1, max_length=4000)
    coach_number: str | None = Field(None, max_length=30)
    department: str | None = Field(None, max_length=120)
    evidence: list[dict] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
class StatusUpdate(BaseModel):
    status: ComplaintStatus
    resolution_note: str | None = Field(None, max_length=4000)
class MediaResponse(BaseModel):
    id: str; media_type: MediaType; original_url: str; annotated_url: str | None; analysis_metadata: str | None; file_name: str; file_size: int; mime_type: str; created_at: datetime
    model_config = {"from_attributes": True}
class ComplaintResponse(BaseModel):
    complaint_id: str; language: str; media_type: MediaType | None; category: str | None; subcategory: str | None; severity: int | None; summary: str | None; suggested_action: str | None; coach_number: str | None; confidence: float | None; department: str | None; status: ComplaintStatus; created_at: datetime; updated_at: datetime; resolved_at: datetime | None; resolution_note: str | None; media: list[MediaResponse]
    model_config = {"from_attributes": True}
class ComplaintCreated(BaseModel): complaint_id: str; status: ComplaintStatus; created_at: datetime
class ComplaintPage(BaseModel): items: list[ComplaintResponse]; page: int; limit: int; total: int; pages: int
