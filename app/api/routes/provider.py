from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_provider, get_current_user
from app.models.user import User
from app.models.booking import BookingStatus
from app.models.service import Service, ServiceCategory
from app.schemas.booking import (
    BookingWithDetails, BookingListResponse, BookingStatusUpdate,
    BookingAcceptedConfirmation,
)
from app.schemas.service import (
    PaginationParams, ServiceWithCategory, ServiceListResponse,
    ProviderServiceCreate, ProviderServiceUpdate,
)
from app.services.provider_service import ProviderService
from app.services.service_service import ServiceCategoryService

router = APIRouter(prefix="/provider", tags=["Provider"])


@router.get(
    "/dashboard",
    summary="Provider dashboard - pending booking requests",
)
async def provider_dashboard(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """
    Provider dashboard showing:
    - Profile summary (name, rating, verification status)
    - List of pending booking requests available to accept
    - Count of active (assigned/in-progress) bookings
    """
    pagination = PaginationParams(page=page, limit=limit)
    provider_service = ProviderService(db)

    # Pending bookings available to accept
    pending_items, pending_total = await provider_service.get_available_bookings(
        str(current_user.id), pagination
    )

    # Active bookings (assigned + in_progress)
    active_items, active_total = await provider_service.get_provider_bookings(
        str(current_user.id), PaginationParams(page=1, limit=100), BookingStatus.ASSIGNED
    )
    in_progress_items, in_progress_total = await provider_service.get_provider_bookings(
        str(current_user.id), PaginationParams(page=1, limit=100), BookingStatus.IN_PROGRESS
    )

    profile = current_user.provider_profile

    return {
        "provider": {
            "id": str(current_user.id),
            "name": current_user.name,
            "phone": current_user.phone,
            "is_verified": profile.is_verified if profile else False,
            "is_available": profile.is_available if profile else False,
            "rating": profile.rating if profile else 0.0,
            "total_reviews": profile.total_reviews if profile else 0,
        },
        "pending_requests": {
            "total": pending_total,
            "page": page,
            "limit": limit,
            "pages": (pending_total + limit - 1) // limit,
            "items": pending_items,
        },
        "active_bookings": {
            "assigned": active_total,
            "in_progress": in_progress_total,
        },
        "message": (
            f"You have {pending_total} pending request(s) waiting for acceptance."
            if pending_total > 0
            else "No pending requests at the moment."
        ),
    }

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


# ─────────────────────────────────────────────
# Provider Service Management
# ─────────────────────────────────────────────

@router.get(
    "/my-services",
    response_model=ServiceListResponse,
    summary="List my service listings",
)
async def list_my_services(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """List all services created by this provider."""
    offset = (page - 1) * limit

    # Count
    count_result = await db.execute(
        select(Service).where(Service.provider_id == current_user.id)
    )
    all_items = count_result.scalars().all()
    total = len(all_items)

    # Paginated with category loaded
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.category))
        .where(Service.provider_id == current_user.id)
        .order_by(Service.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()
    pages = (total + limit - 1) // limit

    return ServiceListResponse(
        items=list(items),
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/my-services",
    response_model=ServiceWithCategory,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new service listing",
)
async def add_my_service(
    service_data: ProviderServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """
    Provider adds a new service listing.
    The service becomes visible to customers immediately.
    Requires a valid category_id from GET /api/v1/services/categories.
    """
    # Verify category exists
    cat_result = await db.execute(
        select(ServiceCategory).where(
            and_(
                ServiceCategory.id == service_data.category_id,
                ServiceCategory.is_active == True,
            )
        )
    )
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive. Check GET /api/v1/services/categories for valid IDs.",
        )

    service = Service(
        category_id=category.id,
        provider_id=current_user.id,
        name=service_data.name,
        description=service_data.description,
        base_price=float(service_data.base_price),
        duration_minutes=service_data.duration_minutes,
        is_active=True,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)

    # Reload with category relationship
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.category))
        .where(Service.id == service.id)
    )
    return result.scalar_one()


@router.patch(
    "/my-services/{service_id}",
    response_model=ServiceWithCategory,
    summary="Update my service listing",
)
async def update_my_service(
    service_id: str,
    service_data: ProviderServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Update a service listing (only the provider who created it)."""
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.category))
        .where(
            and_(
                Service.id == service_id,
                Service.provider_id == current_user.id,
            )
        )
    )
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or you don't own it.",
        )

    update_fields = service_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if field == "base_price":
            value = float(value)
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)

    result = await db.execute(
        select(Service)
        .options(selectinload(Service.category))
        .where(Service.id == service.id)
    )
    return result.scalar_one()


@router.delete(
    "/my-services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove my service listing",
)
async def delete_my_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_provider),
):
    """Soft-delete (deactivate) a service listing."""
    result = await db.execute(
        select(Service).where(
            and_(
                Service.id == service_id,
                Service.provider_id == current_user.id,
            )
        )
    )
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or you don't own it.",
        )

    service.is_active = False
    await db.commit()
    return None