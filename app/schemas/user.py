from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Base ───────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


# ─── Create ─────────────────────────────────────────────────────────────────

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username faqat harf, raqam va _ bo'lishi mumkin")
        return v.lower()


# ─── Update ─────────────────────────────────────────────────────────────────

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# ─── Response ───────────────────────────────────────────────────────────────

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    """Boshqalar ko'rishi uchun (email yashirilgan)."""
    id: int
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Auth ───────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str