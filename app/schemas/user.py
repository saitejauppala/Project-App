from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

from app.models.user import UserRole


# Shared properties
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)


# Registration
class UserRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.CUSTOMER
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove spaces and validate format
        v = v.strip().replace(" ", "")
        # Basic phone validation - should start with + or digit
        if not re.match(r"^[\+]?[0-9]{10,15}$", v):
            raise ValueError("Invalid phone number format")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


# Login
class UserLogin(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=1)


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None


# User response
class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Provider profile schemas
class ProviderProfileBase(BaseModel):
    skills: list = []
    bio: Optional[str] = None


class ProviderProfileCreate(ProviderProfileBase):
    pass


class ProviderProfileResponse(ProviderProfileBase):
    id: str
    user_id: str
    rating: float
    total_reviews: int
    is_available: bool
    is_verified: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class UserWithProfile(UserResponse):
    provider_profile: Optional[ProviderProfileResponse] = None