from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    booking_id: str
    
    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) < 10:
            raise ValueError("Review comment must be at least 10 characters")
        return v


class ReviewResponse(ReviewBase):
    id: str
    booking_id: str
    provider_id: str
    customer_name: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ReviewWithDetails(ReviewResponse):
    service_name: str
    booking_completed_at: Optional[datetime] = None


class ReviewListResponse(BaseModel):
    items: List[ReviewWithDetails]
    total: int
    average_rating: float
    rating_distribution: dict  # {1: count, 2: count, ...}


class ProviderRatingSummary(BaseModel):
    provider_id: str
    provider_name: str
    average_rating: float
    total_reviews: int
    rating_distribution: dict