import json
from datetime import datetime
from math import ceil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.security import get_current_user, require_official, require_passenger
from app.models.complaint import Complaint, ComplaintMedia, ComplaintStatus
from app.models.user import User, UserRole
from app.schemas.complaint import AnalysisResult, ComplaintCreated, ComplaintPage, ComplaintResponse, CreateComplaintRequest, StatusUpdate
from app.services.ai_pipeline import IntegrationError, analyze_complaint
from app.services.complaint_service import change_status, get_complaint_for_user, new_complaint_id, submit_analysis_result
from app.core.config import get_settings
router = APIRouter(prefix="/complaints", tags=["Complaints"])
@router.post("", response_model=ComplaintCreated, status_code=201)
async def create(payload: CreateComplaintRequest, db: Session = Depends(get_db), user: User = Depends(require_passenger)):
    media = db.scalars(select(ComplaintMedia).where(ComplaintMedia.id.in_(payload.media_ids), ComplaintMedia.complaint_id.is_(None))).all()
    if len(media) != len(set(payload.media_ids)): raise HTTPException(422, "One or more media records are unavailable")
    types = {m.media_type for m in media}
    if media and len(types) != 1: raise HTTPException(422, "All media in a complaint must use one media type")
    complaint = Complaint(complaint_id=new_complaint_id(db), user_id=user.id, language=payload.language, media_type=media[0].media_type if media else None)
    db.add(complaint); db.flush()
    for item in media: item.complaint_id = complaint.id
    db.commit(); db.refresh(complaint)

    try:
        source = media[0] if media else None
        source_path = None
        if source and source.original_url.startswith("/media/"):
            source_path = get_settings().local_storage_path / Path(source.original_url).name
        analysis, state = await analyze_complaint(
            source.media_type.value if source else None,
            source_path,
            payload.text,
        )
        submit_analysis_result(db, complaint, analysis, user)
        if source:
            source.analysis_metadata = json.dumps({"evidence": analysis.evidence, "errors": state.errors})
            if state.file_url:
                source.annotated_url = f"/media/{Path(state.file_url).name}"
        db.commit(); db.refresh(complaint)
    except (IntegrationError, RuntimeError) as exc:
        complaint.processing_error = str(exc)
        if complaint.status == ComplaintStatus.submitted:
            change_status(db, complaint, ComplaintStatus.processing, user, "Analysis started")
        if complaint.status == ComplaintStatus.processing:
            change_status(db, complaint, ComplaintStatus.failed, user, "Analysis failed")
        db.commit(); db.refresh(complaint)
    return complaint
@router.get("/{complaint_id}", response_model=ComplaintResponse)
def retrieve(complaint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_complaint_for_user(db, complaint_id, user)
@router.get("", response_model=ComplaintPage)
def list_complaints(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), status: ComplaintStatus | None = None, severity: int | None = Query(None, ge=1, le=5), category: str | None = None, department: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None, search: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Complaint).options(selectinload(Complaint.media))
    if user.role == UserRole.passenger: stmt = stmt.where(Complaint.user_id == user.id)
    if status: stmt = stmt.where(Complaint.status == status)
    if severity: stmt = stmt.where(Complaint.severity == severity)
    if category: stmt = stmt.where(Complaint.category.ilike(f"%{category}%"))
    if department: stmt = stmt.where(Complaint.department.ilike(f"%{department}%"))
    if date_from: stmt = stmt.where(Complaint.created_at >= date_from)
    if date_to: stmt = stmt.where(Complaint.created_at <= date_to)
    if search: stmt = stmt.where(Complaint.complaint_id.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Complaint.created_at.desc()).offset((page-1)*limit).limit(limit)).all()
    return {"items": items, "page": page, "limit": limit, "total": total, "pages": ceil(total / limit) if total else 0}
@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
def update_status(complaint_id: str, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_official)):
    complaint = get_complaint_for_user(db, complaint_id, user)
    change_status(db, complaint, payload.status, user, payload.resolution_note); db.commit(); db.refresh(complaint); return complaint
@router.post("/{complaint_id}/analysis-result", response_model=ComplaintResponse, include_in_schema=True)
def ingest_analysis_result(complaint_id: str, payload: AnalysisResult, db: Session = Depends(get_db), user: User = Depends(require_official)):
    """Internal integration contract. Stores supplied analysis; it never invokes AI."""
    complaint = get_complaint_for_user(db, complaint_id, user)
    submit_analysis_result(db, complaint, payload, user); db.commit(); db.refresh(complaint); return complaint
