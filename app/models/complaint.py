import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class MediaType(str, enum.Enum): image="image"; video="video"; audio="audio"
class ComplaintStatus(str, enum.Enum): submitted="submitted"; processing="processing"; classified="classified"; assigned="assigned"; in_progress="in_progress"; resolved="resolved"; rejected="rejected"
class Complaint(Base):
    __tablename__="complaints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    category: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach_number: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus), default=ComplaintStatus.submitted, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[list["ComplaintMedia"]] = relationship(back_populates="complaint")
class ComplaintMedia(Base):
    __tablename__="complaint_media"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"), nullable=True, index=True)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    original_url: Mapped[str] = mapped_column(String(1000))
    annotated_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    complaint: Mapped[Complaint | None] = relationship(back_populates="media")
class ComplaintStatusHistory(Base):
    __tablename__="complaint_status_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True)
    old_status: Mapped[ComplaintStatus | None] = mapped_column(Enum(ComplaintStatus), nullable=True)
    new_status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus))
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
Index("ix_complaints_status_created", Complaint.status, Complaint.created_at)
