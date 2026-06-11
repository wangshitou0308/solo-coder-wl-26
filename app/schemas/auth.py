from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.core.roles import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    full_name: str = Field(..., max_length=100)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr]
    phone: Optional[str]
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)
