from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_customer
from app.core.redis import rate_limiter, distributed_lock
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingWithDetails,
    BookingListResponse,
)
from app.schemas.service import PaginationParams
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/me", response_model=BookingListResponse)
async def list_my_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[BookingStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """List all bookings for the current user."""
    pagination = PaginationParams(page=page, limit=limit)
    booking_service = BookingService(db)
    
    items, total = await booking_service.get_user_bookings(
        str(current_user.id), pagination, status
    )
    pages = (total + limit - 1) // limit
    
    return BookingListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/me/{booking_id}", response_model=BookingWithDetails)
async def get_my_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Get a specific booking by ID (must belong to current user)."""
    booking_service = BookingService(db)
    booking = await booking_service.get_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    
    if str(booking.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own bookings",
        )
    
    return booking


@router.post(
    "/create",
    response_model=BookingWithDetails,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    request: Request,
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Create a new booking.
    Rate limited: 5 bookings per hour per user.
    Uses distributed lock to prevent duplicate bookings.
    """
    # Rate limiting by user
    rate_key = f"booking_create:{current_user.id}"
    allowed, _, _ = await rate_limiter.is_allowed(rate_key, limit=5, window=3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many booking attempts. Please try again later.",
        )
    
    # Distributed lock to prevent duplicate bookings
    lock_key = f"booking_lock:{current_user.id}:{booking_data.service_id}"
    lock_value = f"{current_user.id}:{booking_data.scheduled_time.timestamp()}"
    
    lock_acquired = await distributed_lock.acquire(
        lock_key, lock_value, expire_seconds=30
    )
    
    if not lock_acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking in progress. Please wait.",
        )
    
    try:
        booking_service = BookingService(db)
        booking = await booking_service.create_booking(
            str(current_user.id), booking_data
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    finally:
        # Always release lock
        await distributed_lock.release(lock_key, lock_value)


@router.patch("/me/{booking_id}", response_model=BookingWithDetails)
async def update_booking(
    booking_id: str,
    update_data: BookingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Update a pending booking."""
    booking_service = BookingService(db)
    
    try:
        booking = await booking_service.update_booking(
            booking_id, str(current_user.id), update_data
        )
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found",
            )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/me/{booking_id}/cancel", response_model=BookingWithDetails)
async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = Query(None, max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Cancel a booking."""
    booking_service = BookingService(db)
    
    try:
        booking = await booking_service.cancel_booking(
            booking_id, str(current_user.id), "customer", reason
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )