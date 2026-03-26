from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingUpdate
from app.schemas.service import PaginationParams
from app.services.booking_lifecycle_service import BookingLifecycleService, TransitionError, AuthorizationError


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID with all relationships."""
        result = await self.db.execute(
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
                selectinload(Booking.provider),
            )
            .where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def get_user_bookings(
        self,
        user_id: str,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None,
    ) -> Tuple[List[Booking], int]:
        """Get all bookings for a user with pagination."""
        query = (
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
                selectinload(Booking.provider),
            )
            .where(Booking.user_id == user_id)
        )
        
        if status:
            query = query.where(Booking.status == status)
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Get paginated results, ordered by most recent first
        query = (
            query.order_by(Booking.created_at.desc())
            .offset((pagination.page - 1) * pagination.limit)
            .limit(pagination.limit)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def has_active_booking(self, user_id: str, service_id: str) -> bool:
        """Check if user has an active booking for this service (with row locking)."""
        active_statuses = [
            BookingStatus.PENDING,
            BookingStatus.ASSIGNED,
            BookingStatus.IN_PROGRESS,
        ]
        
        result = await self.db.execute(
            select(Booking).where(
                and_(
                    Booking.user_id == user_id,
                    Booking.service_id == service_id,
                    Booking.status.in_(active_statuses),
                )
            ).with_for_update()  # Lock rows to prevent race conditions
        )
        return result.scalar_one_or_none() is not None

    async def create_booking(
        self,
        user_id: str,
        booking_data: BookingCreate,
    ) -> Booking:
        """Create a new booking with transaction safety."""
        # Check for duplicate active booking
        if await self.has_active_booking(user_id, booking_data.service_id):
            raise ValueError(
                "You already have an active booking for this service. "
                "Please complete or cancel it before creating a new one."
            )
        
        # Verify service exists and is active
        service_result = await self.db.execute(
            select(Service).where(
                and_(
                    Service.id == booking_data.service_id,
                    Service.is_active == True,
                )
            )
        )
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError("Service not found or is no longer available")
        
        # Create booking within transaction
        booking = Booking(
            user_id=user_id,
            service_id=booking_data.service_id,
            provider_id=None,
            status=BookingStatus.PENDING,
            scheduled_time=booking_data.scheduled_time,
            address=booking_data.address,
            notes=booking_data.notes,
            price=float(service.base_price),
            version=1,
        )
        
        self.db.add(booking)
        await self.db.flush()  # Flush to get booking ID
        await self.db.refresh(booking)
        
        # Eager load relationships for response
        result = await self.db.execute(
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
            )
            .where(Booking.id == booking.id)
        )
        booking = result.scalar_one()
        
        await self.db.commit()
        return booking

    async def update_booking(
        self,
        booking_id: str,
        user_id: str,
        update_data: BookingUpdate,
    ) -> Optional[Booking]:
        """Update a booking (only allowed for pending bookings)."""
        booking = await self.get_by_id(booking_id)
        
        if not booking:
            return None
        
        if booking.user_id != user_id:
            raise ValueError("You can only update your own bookings")
        
        if booking.status != BookingStatus.PENDING:
            raise ValueError("Only pending bookings can be updated")
        
        if update_data.scheduled_time:
            if update_data.scheduled_time < datetime.utcnow():
                raise ValueError("Scheduled time cannot be in the past")
            booking.scheduled_time = update_data.scheduled_time
        
        if update_data.address:
            booking.address = update_data.address
        
        if update_data.notes is not None:
            booking.notes = update_data.notes
        
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def cancel_booking(
        self,
        booking_id: str,
        user_id: str,
        user_role: str,
        reason: Optional[str] = None,
    ) -> Optional[Booking]:
        """Cancel a booking using centralized lifecycle service."""
        lifecycle_service = BookingLifecycleService(self.db)
        
        try:
            return await lifecycle_service.cancel_booking(
                booking_id=booking_id,
                user_id=user_id,
                user_role=user_role,
                reason=reason,
            )
        except (TransitionError, AuthorizationError) as e:
            raise ValueError(str(e))