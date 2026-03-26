from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_provider, get_current_user
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking import (
    BookingWithDetails, BookingListResponse, BookingStatusUpdate,
    BookingAcceptedConfirmation,
)
from app.schemas.service import PaginationParams
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/provider", tags=["Provider"])


@router.get("/available-bookings", response_model=BookingListResponse)
async def list_available_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """List available pending bookings that match provider skills."""
    pagination = PaginationParams(page=page, limit=limit)
    provider_service = ProviderService(db)
    
    items, total = await provider_service.get_available_bookings(
        str(current_user.id), pagination
    )
    pages = (total + limit - 1) // limit
    
    return BookingListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/my-bookings", response_model=BookingListResponse)
async def list_my_assigned_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[BookingStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """List all bookings assigned to this provider."""
    pagination = PaginationParams(page=page, limit=limit)
    provider_service = ProviderService(db)
    
    items, total = await provider_service.get_provider_bookings(
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


@router.get("/bookings/{booking_id}", response_model=BookingWithDetails)
async def get_booking_details(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Get details of a specific booking (must be available or assigned to this provider)."""
    provider_service = ProviderService(db)
    booking = await provider_service.get_booking_for_provider(
        booking_id, str(current_user.id)
    )
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or not accessible",
        )
    
    return booking


@router.post("/bookings/{booking_id}/accept", response_model=BookingAcceptedConfirmation)
async def accept_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """
    Accept a pending booking.
    Assigns the booking to this provider and returns a full confirmation
    with service details, customer info, and appointment time.
    """
    provider_service = ProviderService(db)

    try:
        booking = await provider_service.accept_booking(
            booking_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Build confirmation response
    return BookingAcceptedConfirmation(
        message=f"Booking accepted! You are now assigned to this {booking.service.name} appointment.",
        booking_id=str(booking.id),
        status=booking.status,
        assigned_at=booking.assigned_at,
        # Service info
        service_name=booking.service.name,
        service_category=booking.service.category.name,
        service_duration_minutes=booking.service.duration_minutes,
        service_price=booking.price,
        # Customer info
        customer_name=booking.user.full_name,
        customer_phone=getattr(booking.user, "phone", None),
        # Appointment info
        scheduled_time=booking.scheduled_time,
        address=booking.address,
        notes=booking.notes,
    )


@router.post("/bookings/{booking_id}/start", response_model=BookingWithDetails)
async def start_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Mark booking as in_progress (only assigned provider)."""
    provider_service = ProviderService(db)
    
    try:
        booking = await provider_service.update_booking_status(
            booking_id, str(current_user.id), BookingStatus.IN_PROGRESS
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/bookings/{booking_id}/complete", response_model=BookingWithDetails)
async def complete_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Mark booking as completed (only assigned provider)."""
    provider_service = ProviderService(db)
    
    try:
        booking = await provider_service.update_booking_status(
            booking_id, str(current_user.id), BookingStatus.COMPLETED
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/bookings/{booking_id}/cancel", response_model=BookingWithDetails)
async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = Query(None, max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Cancel an assigned booking (only assigned provider)."""
    provider_service = ProviderService(db)
    
    try:
        booking = await provider_service.cancel_booking(
            booking_id, str(current_user.id), reason
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/stats")
async def get_provider_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Get provider statistics."""
    provider_service = ProviderService(db)
    stats = await provider_service.get_provider_stats(str(current_user.id))
    return stats