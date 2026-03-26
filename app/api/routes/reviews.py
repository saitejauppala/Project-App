from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_customer
from app.core.redis import rate_limiter
from app.models.user import User
from app.schemas.review import (
    ReviewCreate, ReviewResponse, ReviewWithDetails,
    ReviewListResponse, ProviderRatingSummary,
)
from app.services.review_service import ReviewService, ReviewError

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Create a review for a completed booking.
    Rate limited: 10 reviews per hour per user.
    """
    # Rate limiting
    rate_key = f"reviews:create:{current_user.id}"
    allowed, _, _ = await rate_limiter.is_allowed(rate_key, limit=10, window=3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many review attempts. Please try again later.",
        )
    
    review_service = ReviewService(db)
    
    try:
        review = await review_service.create_review(
            str(current_user.id), review_data
        )
        return review
    except ReviewError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/booking/{booking_id}/can-review")
async def can_review(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Check if the current user can review a specific booking."""
    review_service = ReviewService(db)
    
    can_review, error_message = await review_service.can_review_booking(
        str(current_user.id), booking_id
    )
    
    return {
        "can_review": can_review,
        "error": error_message,
    }


@router.get("/provider/{provider_id}", response_model=ReviewListResponse)
async def get_provider_reviews(
    provider_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all reviews for a provider."""
    review_service = ReviewService(db)
    
    result = await review_service.get_provider_reviews(
        provider_id, page=page, limit=limit
    )
    
    return ReviewListResponse(**result)


@router.get("/provider/{provider_id}/summary")
async def get_provider_rating_summary(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get rating summary for a provider."""
    from sqlalchemy import select
    from app.models.user import ProviderProfile, User
    
    # Get provider with user info
    result = await db.execute(
        select(ProviderProfile, User)
        .join(User, ProviderProfile.user_id == User.id)
        .where(ProviderProfile.id == provider_id)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    
    provider, user = row
    
    # Get rating distribution
    review_service = ReviewService(db)
    distribution = await review_service._get_rating_distribution(provider_id)
    
    return {
        "provider_id": provider_id,
        "provider_name": user.name,
        "average_rating": float(provider.rating),
        "total_reviews": provider.total_reviews,
        "rating_distribution": distribution,
    }


@router.get("/my-reviews")
async def get_my_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Get all reviews written by the current user."""
    from sqlalchemy import select
    from app.models.review import Review
    from app.models.booking import Booking
    from app.models.service import Service
    from app.models.user import User
    
    # Get reviews by this user
    query = (
        select(Review, Booking, Service, User)
        .join(Booking, Review.booking_id == Booking.id)
        .join(Service, Booking.service_id == Service.id)
        .join(User, Review.provider_id == User.id)
        .where(Booking.user_id == current_user.id)
        .order_by(Review.created_at.desc())
    )
    
    # Get total
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(Booking.user_id == current_user.id)
            .subquery()
        )
    )
    total = count_result.scalar()
    
    # Get paginated
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    reviews = []
    for review, booking, service, provider_user in rows:
        reviews.append({
            "id": str(review.id),
            "booking_id": str(review.booking_id),
            "provider_id": str(review.provider_id),
            "provider_name": provider_user.name,
            "rating": review.rating,
            "comment": review.comment,
            "service_name": service.name,
            "created_at": review.created_at,
        })
    
    return {
        "items": reviews,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }