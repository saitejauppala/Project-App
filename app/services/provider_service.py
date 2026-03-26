from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.user import User, ProviderProfile
from app.schemas.service import PaginationParams
from app.services.booking_lifecycle_service import BookingLifecycleService, TransitionError, AuthorizationError


class ProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_provider_profile(self, user_id: str) -> Optional[ProviderProfile]:
        """Get provider profile by user ID."""
        result = await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_available_bookings(
        self, provider_id: str, pagination: PaginationParams
    ) -> Tuple[List[Booking], int]:
        """Get pending bookings that match provider skills."""
        # Get provider skills
        profile = await self.get_provider_profile(provider_id)
        if not profile:
            return [], 0
        
        provider_skills = profile.skills or []
        
        # Build query for pending bookings
        # Match by service_id in provider skills, or show all if no skills specified
        query = (
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
            )
            .where(
                and_(
                    Booking.status == BookingStatus.PENDING,
                    Booking.provider_id.is_(None),
                )
            )
        )
        
        # If provider has skills, filter by matching service IDs
        if provider_skills:
            query = query.where(Booking.service_id.in_(provider_skills))
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Get paginated results
        query = (
            query.order_by(Booking.scheduled_time.asc())
            .offset((pagination.page - 1) * pagination.limit)
            .limit(pagination.limit)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def get_provider_bookings(
        self,
        provider_id: str,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None,
    ) -> Tuple[List[Booking], int]:
        """Get all bookings assigned to this provider."""
        query = (
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
            )
            .where(Booking.provider_id == provider_id)
        )
        
        if status:
            query = query.where(Booking.status == status)
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Get paginated results
        query = (
            query.order_by(Booking.scheduled_time.asc())
            .offset((pagination.page - 1) * pagination.limit)
            .limit(pagination.limit)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def get_booking_for_provider(
        self, booking_id: str, provider_id: str
    ) -> Optional[Booking]:
        """Get booking if it's available or assigned to this provider."""
        result = await self.db.execute(
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
                selectinload(Booking.provider),
            )
            .where(
                and_(
                    Booking.id == booking_id,
                    or_(
                        Booking.status == BookingStatus.PENDING,
                        Booking.provider_id == provider_id,
                    ),
                )
            )
        )
        return result.scalar_one_or_none()

    async def accept_booking(
        self, booking_id: str, provider_id: str
    ) -> Booking:
        """Accept a pending booking (assign to provider with row locking)."""
        # Lock the booking row to prevent double assignment
        result = await self.db.execute(
            select(Booking)
            .where(
                and_(
                    Booking.id == booking_id,
                    Booking.status == BookingStatus.PENDING,
                    Booking.provider_id.is_(None),
                )
            )
            .with_for_update()  # Lock row for update
        )
        booking = result.scalar_one_or_none()
        
        if not booking:
            raise ValueError(
                "Booking not available. It may have been already assigned or cancelled."
            )
        
        # Verify provider has skills for this service (optional check)
        profile = await self.get_provider_profile(provider_id)
        if profile and profile.skills:
            if str(booking.service_id) not in profile.skills:
                raise ValueError(
                    "You don't have the required skills for this service."
                )
        
        # Assign booking to provider
        booking.provider_id = provider_id
        booking.status = BookingStatus.ASSIGNED
        booking.assigned_at = datetime.utcnow()
        booking.version += 1  # Increment version for optimistic locking
        
        await self.db.commit()
        
        # Reload with relationships
        result = await self.db.execute(
            select(Booking)
            .options(
                selectinload(Booking.service).selectinload(Service.category),
                selectinload(Booking.user),
                selectinload(Booking.provider),
            )
            .where(Booking.id == booking_id)
        )
        return result.scalar_one()

    async def update_booking_status(
        self,
        booking_id: str,
        provider_id: str,
        new_status: BookingStatus,
    ) -> Booking:
        """Update booking status using centralized lifecycle service."""
        lifecycle_service = BookingLifecycleService(self.db)
        
        try:
            return await lifecycle_service.transition_status(
                booking_id=booking_id,
                new_status=new_status,
                user_id=provider_id,
                user_role="provider",
            )
        except (TransitionError, AuthorizationError) as e:
            raise ValueError(str(e))

    async def cancel_booking(
        self,
        booking_id: str,
        provider_id: str,
        reason: Optional[str] = None,
    ) -> Booking:
        """Cancel a booking (provider can only cancel assigned bookings)."""
        lifecycle_service = BookingLifecycleService(self.db)
        
        try:
            return await lifecycle_service.cancel_booking(
                booking_id=booking_id,
                user_id=provider_id,
                user_role="provider",
                reason=reason,
            )
        except (TransitionError, AuthorizationError) as e:
            raise ValueError(str(e))

    async def get_provider_stats(self, provider_id: str) -> dict:
        """Get provider statistics."""
        # Total bookings
        total_result = await self.db.execute(
            select(func.count()).where(Booking.provider_id == provider_id)
        )
        total_bookings = total_result.scalar()
        
        # By status
        status_counts = {}
        for status in BookingStatus:
            count_result = await self.db.execute(
                select(func.count()).where(
                    and_(
                        Booking.provider_id == provider_id,
                        Booking.status == status,
                    )
                )
            )
            status_counts[status.value] = count_result.scalar()
        
        # Completed bookings
        completed_result = await self.db.execute(
            select(func.count()).where(
                and_(
                    Booking.provider_id == provider_id,
                    Booking.status == BookingStatus.COMPLETED,
                )
            )
        )
        completed = completed_result.scalar()
        
        return {
            "total_bookings": total_bookings,
            "completed_bookings": completed,
            "by_status": status_counts,
        }