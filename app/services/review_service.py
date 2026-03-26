from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import Review
from app.models.booking import Booking, BookingStatus
from app.models.user import User, ProviderProfile
from app.models.service import Service
from app.schemas.review import ReviewCreate


class ReviewError(Exception):
    """Raised when review operation fails."""
    pass


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_review_by_booking(self, booking_id: str) -> Optional[Review]:
        """Check if a review already exists for this booking."""
        result = await self.db.execute(
            select(Review).where(Review.booking_id == booking_id)
        )
        return result.scalar_one_or_none()

    async def get_review_by_id(self, review_id: str) -> Optional[Review]:
        """Get review by ID with relationships."""
        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.provider),
                selectinload(Review.booking),
            )
            .where(Review.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_provider_reviews(
        self,
        provider_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> Dict:
        """Get all reviews for a provider with statistics."""
        # Get reviews with booking and user info
        query = (
            select(Review, Booking, User, Service)
            .join(Booking, Review.booking_id == Booking.id)
            .join(User, Booking.user_id == User.id)
            .join(Service, Booking.service_id == Service.id)
            .where(Review.provider_id == provider_id)
            .order_by(Review.created_at.desc())
        )
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(
                select(Review).where(Review.provider_id == provider_id).subquery()
            )
        )
        total = count_result.scalar()
        
        # Get paginated results
        query = query.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()
        
        # Build review list
        reviews = []
        for review, booking, user, service in rows:
            reviews.append({
                "id": str(review.id),
                "booking_id": str(review.booking_id),
                "provider_id": str(review.provider_id),
                "rating": review.rating,
                "comment": review.comment,
                "customer_name": user.name,
                "service_name": service.name,
                "booking_completed_at": booking.completed_at,
                "created_at": review.created_at,
            })
        
        # Get rating distribution
        distribution = await self._get_rating_distribution(provider_id)
        
        # Get provider stats
        provider_result = await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.id == provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        
        return {
            "items": reviews,
            "total": total,
            "average_rating": float(provider.rating) if provider else 0.0,
            "rating_distribution": distribution,
        }

    async def _get_rating_distribution(self, provider_id: str) -> Dict[int, int]:
        """Get rating distribution for a provider."""
        result = await self.db.execute(
            select(Review.rating, func.count())
            .where(Review.provider_id == provider_id)
            .group_by(Review.rating)
        )
        
        # Initialize all ratings with 0
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating, count in result.all():
            distribution[rating] = count
        
        return distribution

    async def create_review(
        self,
        user_id: str,
        review_data: ReviewCreate,
    ) -> Review:
        """
        Create a review for a completed booking.
        Updates provider rating using optimized calculation.
        """
        # Check if review already exists for this booking
        existing = await self.get_review_by_booking(review_data.booking_id)
        if existing:
            raise ReviewError("A review already exists for this booking")
        
        # Get booking with lock
        result = await self.db.execute(
            select(Booking)
            .options(selectinload(Booking.service))
            .where(Booking.id == review_data.booking_id)
            .with_for_update()
        )
        booking = result.scalar_one_or_none()
        
        if not booking:
            raise ReviewError("Booking not found")
        
        # Verify booking belongs to user
        if str(booking.user_id) != user_id:
            raise ReviewError("You can only review your own bookings")
        
        # Verify booking is completed
        if booking.status != BookingStatus.COMPLETED:
            raise ReviewError(
                f"Cannot review a booking with status '{booking.status.value}'. "
                "Only completed bookings can be reviewed."
            )
        
        # Verify booking has a provider assigned
        if not booking.provider_id:
            raise ReviewError("Cannot review a booking without an assigned provider")
        
        # Get provider profile with lock
        provider_result = await self.db.execute(
            select(ProviderProfile)
            .where(ProviderProfile.user_id == booking.provider_id)
            .with_for_update()
        )
        provider = provider_result.scalar_one_or_none()
        
        if not provider:
            raise ReviewError("Provider not found")
        
        # Create review
        review = Review(
            booking_id=review_data.booking_id,
            provider_id=provider.id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        
        self.db.add(review)
        
        # Update provider rating using sum+count (prevents floating point drift)
        provider.rating_sum += review_data.rating
        provider.rating_count += 1
        provider.total_reviews = provider.rating_count
        provider.rating = provider.rating_sum / provider.rating_count
        
        await self.db.commit()
        await self.db.refresh(review)
        
        # Load relationships for response
        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.provider),
                selectinload(Review.booking).selectinload(Booking.user),
            )
            .where(Review.id == review.id)
        )
        return result.scalar_one()

    async def can_review_booking(
        self,
        user_id: str,
        booking_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a user can review a booking.
        
        Returns:
            (can_review, error_message)
        """
        # Check if review already exists
        existing = await self.get_review_by_booking(booking_id)
        if existing:
            return False, "A review already exists for this booking"
        
        # Get booking
        result = await self.db.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()
        
        if not booking:
            return False, "Booking not found"
        
        if str(booking.user_id) != user_id:
            return False, "You can only review your own bookings"
        
        if booking.status != BookingStatus.COMPLETED:
            return False, f"Cannot review a booking with status '{booking.status.value}'"
        
        if not booking.provider_id:
            return False, "Cannot review a booking without an assigned provider"
        
        return True, None