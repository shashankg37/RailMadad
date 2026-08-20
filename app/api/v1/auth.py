from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
router = APIRouter(prefix="/auth", tags=["Authentication"])
@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)): raise HTTPException(409, "Email is already registered")
    if payload.role != UserRole.passenger:
        raise HTTPException(403, "Public registration is limited to passengers")
    user = User(name=payload.name, email=str(payload.email), phone=payload.phone, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user); db.commit(); db.refresh(user); return user
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))
@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)): return user
