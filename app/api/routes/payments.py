from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_customer
from app.core.redis import rate_limiter
from app.models.user import User
from app.services.payment_service import PaymentService, PaymentError, SignatureError
from app.services.booking_service import BookingService
from app.schemas.booking import BookingWithDetails

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create-order")
async def create_payment_order(
    request: Request,
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Create a Razorpay payment order for a booking.
    Only the booking owner can create a payment order.
    Rate limited: 10 orders per minute per user.
    """
    # Rate limiting by user
    rate_key = f"payment_orders:{current_user.id}"
    allowed, _, _ = await rate_limiter.is_allowed(rate_key, limit=10, window=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many payment attempts. Please try again later.",
        )
    
    # Verify booking belongs to user
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
            detail="You can only pay for your own bookings",
        )
    
    # Create payment order
    payment_service = PaymentService(db)
    
    try:
        order = await payment_service.create_payment_order(
            booking_id=booking_id,
            amount=booking.price,
        )
        return order
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Razorpay webhook endpoint for payment notifications.
    This is called by Razorpay when payment status changes.
    """
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify signature (in production, use webhook secret)
    # For now, we process the webhook (add verification in production)
    
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    
    event = payload.get("event")
    payment_service = PaymentService(db)
    
    try:
        if event == "payment.captured":
            # Payment successful
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            amount = payment_entity.get("amount")  # Amount in paise
            
            if order_id and payment_id:
                await payment_service.process_payment_success(
                    razorpay_order_id=order_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature=x_razorpay_signature or "",
                    razorpay_amount=amount,
                )
        
        elif event == "payment.failed":
            # Payment failed
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            
            if order_id:
                await payment_service.process_payment_failure(
                    razorpay_order_id=order_id,
                    error_code=payment_entity.get("error_code"),
                    error_description=payment_entity.get("error_description"),
                )
        
        # Return success to Razorpay
        return {"status": "ok"}
    
    except PaymentError as e:
        # Log error but return 200 to prevent Razorpay retries
        # (you might want to retry for some errors)
        print(f"Payment processing error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/booking/{booking_id}/status")
async def get_payment_status(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get payment status for a booking."""
    # Verify access
    booking_service = BookingService(db)
    booking = await booking_service.get_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    
    # Check authorization (customer, assigned provider, or admin)
    user_id = str(current_user.id)
    user_role = current_user.role.value
    
    has_access = (
        user_role == "admin" or
        str(booking.user_id) == user_id or
        (booking.provider_id and str(booking.provider_id) == user_id)
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment_by_booking(booking_id)
    
    if not payment:
        return {
            "booking_id": booking_id,
            "payment_status": None,
            "amount": None,
        }
    
    return {
        "booking_id": booking_id,
        "payment_id": str(payment.id),
        "payment_status": payment.status.value,
        "amount": float(payment.amount),
        "razorpay_order_id": payment.razorpay_order_id,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "paid_at": payment.paid_at,
    }


@router.post("/verify")
async def verify_payment(
    order_id: str,
    payment_id: str,
    signature: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Verify payment signature from frontend (optional manual verification).
    Webhook is the primary source of truth.
    """
    payment_service = PaymentService(db)
    
    is_valid = await payment_service.verify_payment_signature(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )
    
    # Get payment details
    payment = await payment_service.get_payment_by_order_id(order_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    
    return {
        "valid": True,
        "payment_status": payment.status.value,
        "booking_id": str(payment.booking_id),
    }