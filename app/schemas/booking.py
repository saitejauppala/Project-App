from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

from app.models.booking import BookingStatus
from app.schemas.service import ServiceResponse, ServiceWithCategory
from app.schemas.user import UserResponse


# Booking Schemas
class BookingBase(BaseModel):
    service_id: str
    scheduled_time: datetime
    address: str = Field(..., min_length=10, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class BookingCreate(BookingBase):
    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time(cls, v: datetime) -> datetime:
        if v < datetime.utcnow():
            raise ValueError("Scheduled time cannot be in the past")
        return v


class BookingUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    address: Optional[str] = Field(None, min_length=10, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class BookingResponse(BaseModel):
    id: str
    user_id: str
    service_id: str
    provider_id: Optional[str] = None
    status: BookingStatus
    scheduled_time: datetime
    address: str
    notes: Optional[str] = None
    price: Decimal
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BookingWithDetails(BookingResponse):
    service: ServiceWithCategory
    user: UserResponse
    provider: Optional[UserResponse] = None


# Pagination
class BookingListResponse(BaseModel):
    items: List[BookingWithDetails]
    total: int
    page: int
    limit: int
    pages: int


# Status update schemas
class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    reason: Optional[str] = Field(None, max_length=500)


class ProviderAssignment(BaseModel):
    provider_id: str