from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory
from app.models.user import User, UserRole
from app.schemas.complaint import AnalysisResult
from app.services.ai_pipeline import DEPARTMENT_ROUTING, safety_and_departments

TRANSITIONS = {
    ComplaintStatus.submitted: {ComplaintStatus.processing, ComplaintStatus.rejected},
    ComplaintStatus.processing: {ComplaintStatus.classified, ComplaintStatus.rejected},
    ComplaintStatus.classified: {ComplaintStatus.assigned, ComplaintStatus.rejected},
    ComplaintStatus.assigned: {ComplaintStatus.in_progress, ComplaintStatus.resolved, ComplaintStatus.rejected},
    ComplaintStatus.in_progress: {ComplaintStatus.resolved, ComplaintStatus.rejected, ComplaintStatus.failed},
    ComplaintStatus.resolved: set(),
    ComplaintStatus.rejected: set(),
    ComplaintStatus.failed: set(),
}


def new_complaint_id(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.complaint_id.like(f"RM-{year}-%"))) or 0
    return f"RM-{year}-{count + 1:06d}"


def change_status(db: Session, complaint: Complaint, new_status: ComplaintStatus, actor: User | None, note: str | None = None, internal=False):
    if new_status == complaint.status:
        return
    if new_status not in TRANSITIONS[complaint.status]:
        raise HTTPException(422, "Invalid complaint status transition")
    old = complaint.status
    complaint.status = new_status
    if new_status == ComplaintStatus.resolved:
        complaint.resolved_at = datetime.utcnow()
        complaint.resolution_note = note
    db.add(
        ComplaintStatusHistory(
            complaint_id=complaint.id,
            old_status=old,
            new_status=new_status,
            changed_by=actor.id if actor else None,
            note=note,
        )
    )


def submit_analysis_result(db: Session, complaint: Complaint, analysis: AnalysisResult, actor: User | None = None) -> Complaint:
    complaint.category, complaint.subcategory = analysis.category, analysis.subcategory
    complaint.severity, complaint.summary = analysis.severity, analysis.summary
    complaint.suggested_action, complaint.coach_number, complaint.confidence = analysis.suggested_action, analysis.coach_number, analysis.confidence

    detected_label = analysis.category.strip().lower()
    routing = DEPARTMENT_ROUTING.get(detected_label, [])
    if analysis.department:
        complaint.department = analysis.department
        complaint.departments = analysis.department
    elif routing:
        complaint.department = routing[0]
        complaint.departments = "; ".join(routing)
    else:
        complaint.department = None
        complaint.departments = None

    final_severity, assigned_departments, safety_audit = safety_and_departments([], analysis.severity)
    complaint.severity = final_severity
    complaint.department = assigned_departments[0] if assigned_departments else complaint.department
    complaint.departments = "; ".join(assigned_departments) if assigned_departments else complaint.departments
    complaint.processing_times = str({"safety_audit": safety_audit})

    if complaint.status == ComplaintStatus.submitted:
        change_status(db, complaint, ComplaintStatus.processing, actor, "Analysis result received")
    if complaint.status == ComplaintStatus.processing:
        change_status(db, complaint, ComplaintStatus.classified, actor, "Analysis result stored")
    return complaint


def get_complaint_for_user(db: Session, complaint_id: str, user: User) -> Complaint:
    complaint = db.scalar(select(Complaint).where(Complaint.complaint_id == complaint_id))
    if not complaint:
        raise HTTPException(404, "Complaint was not found")
    if user.role == UserRole.passenger and complaint.user_id != user.id:
        raise HTTPException(403, "Not permitted to access this complaint")
    return complaint
