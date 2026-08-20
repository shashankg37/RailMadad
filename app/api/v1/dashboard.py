from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_official
from app.models.complaint import Complaint
router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_official)])
def grouped(db, column): return [{"value": v or "unclassified", "count": c} for v,c in db.execute(select(column, func.count()).group_by(column)).all()]
@router.get("/summary")
def summary(db: Session = Depends(get_db)): return {"total": db.scalar(select(func.count()).select_from(Complaint)) or 0, "open": db.scalar(select(func.count()).select_from(Complaint).where(Complaint.status.not_in(["resolved", "rejected"]))) or 0}
@router.get("/categories")
def categories(db: Session = Depends(get_db)): return grouped(db, Complaint.category)
@router.get("/severity")
def severity(db: Session = Depends(get_db)): return grouped(db, Complaint.severity)
@router.get("/status")
def status(db: Session = Depends(get_db)): return grouped(db, Complaint.status)
@router.get("/trends")
def trends(db: Session = Depends(get_db)): return [{"date": str(day), "count": count} for day,count in db.execute(select(func.date(Complaint.created_at), func.count()).group_by(func.date(Complaint.created_at)).order_by(func.date(Complaint.created_at))).all()]
