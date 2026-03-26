from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.user import User
from app.models.payment import Payment, PaymentStatus


class TransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class AuthorizationError(Exception):
    """Raised when user is not authorized for an action."""
    pass


class BookingLifecycleService:
    """Centralized service for booking status transitions and lifecycle management."""
    
    # Define valid status transitions
    VALID_TRANSITIONS: Dict[BookingStatus, List[BookingStatus]] = {
        BookingStatus.PENDING: [
            BookingStatus.ASSIGNED,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.ASSIGNED: [
            BookingStatus.IN_PROGRESS,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.IN_PROGRESS: [
            BookingStatus.COMPLETED,
            BookingStatus.CANCELLED,
        ],
        BookingStatus.COMPLETED: [],  # Terminal state
        BookingStatus.CANCELLED: [],  # Terminal state
    }
    
    # Define who can cancel at each status
    CANCELLATION_RULES: Dict[BookingStatus, List[str]] = {
        BookingStatus.PENDING: ["customer", "admin"],
        BookingStatus.ASSIGNED: ["customer", "provider", "admin"],
        BookingStatus.IN_PROGRESS: ["admin"],  # Only admin can cancel in-progress
        BookingStatus.COMPLETED: [],
        BookingStatus.CANCELLED: [],
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _is_valid_transition(self, from_status: BookingStatus, to_status: BookingStatus) -> bool:
        """Check if a status transition is valid."""
        allowed = self.VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed
    
    def _get_transition_error_message(
        self, from_status: BookingStatus, to_status: BookingStatus
    ) -> str:
        """Get a descriptive error message for invalid transitions."""
        allowed = self.VALID_TRANSITIONS.get(from_status, [])
        allowed_str = ", ".join([s.value for s in allowed]) if allowed else "none (terminal state)"
        return (
            f"Cannot transition from '{from_status.value}' to '{to_status.value}'. "
            f"Allowed transitions: {allowed_str}"
        )
    
    async def _get_booking_with_lock(self, booking_id: str) -> Optional[Booking]:
        """Get booking with row locking for updates."""
        result = await self.db.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()
    
    async def _get_booking_with_relations(self, booking_id: str) -> Optional[Booking]:
        """Get booking with all relationships loaded."""
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
    
    async def transition_status(
        self,
        booking_id: str,
        new_status: BookingStatus,
        user_id: str,
        user_role: str,
        reason: Optional[str] = None,
    ) -> Booking:
        """
        Centralized method to transition booking status.
        
        Args:
            booking_id: The booking ID
            new_status: Target status
            user_id: User making the transition
            user_role: Role of the user (customer, provider, admin)
            reason: Optional reason for the transition
            
        Returns:
            Updated booking
            
        Raises:
            TransitionError: If transition is invalid
            AuthorizationError: If user not authorized
        """
        # Lock and get booking
        booking = await self._get_booking_with_lock(booking_id)
        
        if not booking:
            raise TransitionError("Booking not found")
        
        current_status = booking.status
        
        # Validate transition
        if not self._is_valid_transition(current_status, new_status):
            raise TransitionError(
                self._get_transition_error_message(current_status, new_status)
            )
        
        # Validate authorization based on transition type
        await self._validate_transition_auth(
            booking, current_status, new_status, user_id, user_role
        )
        
        # Perform transition
        booking.status = new_status
        booking.version += 1
        
        # Update timestamps based on status
        if new_status == BookingStatus.ASSIGNED:
            booking.provider_id = user_id if user_role == "provider" else booking.provider_id
            booking.assigned_at = datetime.utcnow()
        elif new_status == BookingStatus.IN_PROGRESS:
            booking.started_at = datetime.utcnow()
        elif new_status == BookingStatus.COMPLETED:
            booking.completed_at = datetime.utcnow()
        elif new_status == BookingStatus.CANCELLED:
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = reason
        
        await self.db.commit()
        
        # Return with relationships
        return await self._get_booking_with_relations(booking_id)
    
    async def _validate_transition_auth(
        self,
        booking: Booking,
        current_status: BookingStatus,
        new_status: BookingStatus,
        user_id: str,
        user_role: str,
    ):
        """Validate user authorization for a status transition."""
        
        # Admin can do anything
        if user_role == "admin":
            return
        
        # Provider assignments
        if new_status == BookingStatus.ASSIGNED:
            if user_role != "provider":
                raise AuthorizationError("Only providers can accept bookings")
            if booking.provider_id and booking.provider_id != user_id:
                raise AuthorizationError("Booking already assigned to another provider")
            # Check payment status before assignment
            await self._validate_payment_for_assignment(booking)
            return
        
        # Provider starting service
        if new_status == BookingStatus.IN_PROGRESS:
            if user_role != "provider":
                raise AuthorizationError("Only providers can start bookings")
            if str(booking.provider_id) != user_id:
                raise AuthorizationError("You are not assigned to this booking")
            # Check payment status before starting
            await self._validate_payment_for_assignment(booking)
            return
        
        # Provider completing service
        if new_status == BookingStatus.COMPLETED:
            if user_role != "provider":
                raise AuthorizationError("Only providers can complete bookings")
            if str(booking.provider_id) != user_id:
                raise AuthorizationError("You are not assigned to this booking")
            return
        
        # Customer actions
        if user_role == "customer":
            if str(booking.user_id) != user_id:
                raise AuthorizationError("You can only modify your own bookings")
            
            # Customer cancellations
            if new_status == BookingStatus.CANCELLED:
                allowed = self.CANCELLATION_RULES.get(current_status, [])
                if "customer" not in allowed:
                    raise AuthorizationError(
                        f"Cannot cancel booking in '{current_status.value}' status"
                    )
                return
        
        # Provider cancellations
        if user_role == "provider" and new_status == BookingStatus.CANCELLED:
            allowed = self.CANCELLATION_RULES.get(current_status, [])
            if "provider" not in allowed:
                raise AuthorizationError(
                    f"Cannot cancel booking in '{current_status.value}' status"
                )
            if str(booking.provider_id) != user_id:
                raise AuthorizationError("You are not assigned to this booking")
            return
        
        raise AuthorizationError("Not authorized for this action")
    
    async def cancel_booking(
        self,
        booking_id: str,
        user_id: str,
        user_role: str,
        reason: Optional[str] = None,
    ) -> Booking:
        """
        Cancel a booking with proper authorization checks.
        
        Args:
            booking_id: The booking ID
            user_id: User cancelling
            user_role: Role of the user
            reason: Cancellation reason
            
        Returns:
            Updated booking
        """
        return await self.transition_status(
            booking_id=booking_id,
            new_status=BookingStatus.CANCELLED,
            user_id=user_id,
            user_role=user_role,
            reason=reason,
        )
    
    async def get_booking_status_history(self, booking_id: str) -> List[Dict]:
        """
        Get simplified status history for a booking.
        (Full audit trail would require a separate audit table)
        """
        booking = await self._get_booking_with_relations(booking_id)
        
        if not booking:
            return []
        
        # Build history from timestamps
        history = []
        
        history.append({
            "status": "created",
            "timestamp": booking.created_at,
            "by": "system",
        })
        
        if booking.assigned_at:
            history.append({
                "status": "assigned",
                "timestamp": booking.assigned_at,
                "by": str(booking.provider_id) if booking.provider_id else "unknown",
            })
        
        if booking.started_at:
            history.append({
                "status": "started",
                "timestamp": booking.started_at,
                "by": str(booking.provider_id) if booking.provider_id else "unknown",
            })
        
        if booking.completed_at:
            history.append({
                "status": "completed",
                "timestamp": booking.completed_at,
                "by": str(booking.provider_id) if booking.provider_id else "unknown",
            })
        
        if booking.cancelled_at:
            history.append({
                "status": "cancelled",
                "timestamp": booking.cancelled_at,
                "by": "user",
                "reason": booking.cancellation_reason,
            })
        
        return history
    
    async def _validate_payment_for_assignment(self, booking: Booking):
        """Validate that payment is completed before allowing assignment/start."""
        # Get payment for this booking
        result = await self.db.execute(
            select(Payment).where(Payment.booking_id == booking.id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise AuthorizationError(
                "Payment required before proceeding. Please complete payment first."
            )
        
        if payment.status != PaymentStatus.SUCCESS:
            raise AuthorizationError(
                f"Payment not completed (status: {payment.status.value}). "
                "Please complete payment before proceeding."
            )
    
    async def get_payment_status(self, booking_id: str) -> Optional[str]:
        """Get payment status for a booking."""
        result = await self.db.execute(
            select(Payment).where(Payment.booking_id == booking_id)
        )
        payment = result.scalar_one_or_none()
        return payment.status.value if payment else None
    
    async def can_user_cancel(
        self, booking: Booking, user_id: str, user_role: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a user can cancel a booking and return reason if not.
        
        Returns:
            (can_cancel, error_message)
        """
        # Admin can always cancel
        if user_role == "admin":
            return True, None
        
        # Check if status allows cancellation
        allowed_roles = self.CANCELLATION_RULES.get(booking.status, [])
        
        if user_role not in allowed_roles:
            return False, f"Cannot cancel booking in '{booking.status.value}' status"
        
        # Check ownership
        if user_role == "customer" and str(booking.user_id) != user_id:
            return False, "You can only cancel your own bookings"
        
        if user_role == "provider" and str(booking.provider_id) != user_id:
            return False, "You can only cancel bookings assigned to you"
        
        return True, None