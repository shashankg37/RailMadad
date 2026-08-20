from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(None, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.passenger
class LoginRequest(BaseModel): email: EmailStr; password: str
class TokenResponse(BaseModel): access_token: str; token_type: str = "bearer"
class UserResponse(BaseModel):
    id: str; name: str; email: EmailStr; phone: str | None; role: UserRole; is_active: bool; created_at: datetime
    model_config = {"from_attributes": True}
