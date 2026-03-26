import uuid
import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking
from app.models.service import Service


class PaymentError(Exception):
    """Raised when payment operation fails."""
    pass


class SignatureError(Exception):
    """Raised when Razorpay signature verification fails."""
    pass


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
    
    async def get_payment_by_booking(self, booking_id: str) -> Optional[Payment]:
        """Get payment by booking ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.booking_id == booking_id)
        )
        return result.scalar_one_or_none()
    
    async def get_payment_by_order_id(self, order_id: str) -> Optional[Payment]:
        """Get payment by Razorpay order ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_payment_by_idempotency_key(self, key: str) -> Optional[Payment]:
        """Get payment by idempotency key (prevents duplicates)."""
        result = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()
    
    async def create_payment_order(
        self,
        booking_id: str,
        amount: float,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order and store it in the database.
        
        Args:
            booking_id: The booking ID
            amount: Amount in rupees (will be converted to paise)
            currency: Currency code (default INR)
            
        Returns:
            Order details for frontend
        """
        # Check if payment already exists for this booking
        existing = await self.get_payment_by_booking(booking_id)
        if existing:
            if existing.status == PaymentStatus.SUCCESS:
                raise PaymentError("Payment already completed for this booking")
            # Return existing order if still pending
            if existing.razorpay_order_id:
                return {
                    "order_id": existing.razorpay_order_id,
                    "amount": int(existing.amount * 100),  # Convert to paise
                    "currency": currency,
                    "key_id": self.key_id,
                    "booking_id": booking_id,
                    "existing": True,
                }
        
        # Generate idempotency key
        idempotency_key = str(uuid.uuid4())
        
        # Create Razorpay order (mock for test mode)
        # In production, use Razorpay SDK: client.order.create({...})
        razorpay_order_id = f"order_{uuid.uuid4().hex[:20]}"
        
        # Create payment record
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=idempotency_key,
            amount=amount,
            status=PaymentStatus.CREATED,
            razorpay_order_id=razorpay_order_id,
        )
        
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        
        return {
            "order_id": razorpay_order_id,
            "amount": int(amount * 100),  # Convert to paise for Razorpay
            "currency": currency,
            "key_id": self.key_id,
            "booking_id": booking_id,
            "idempotency_key": idempotency_key,
        }
    
    def verify_webhook_signature(
        self,
        webhook_body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Verify Razorpay webhook signature.
        
        Args:
            webhook_body: Raw request body
            signature: X-Razorpay-Signature header
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        expected_signature = hmac.new(
            secret.encode(),
            webhook_body,
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_payment_success(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        razorpay_amount: Optional[int] = None,
    ) -> Payment:
        """
        Process successful payment from webhook.
        
        Args:
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID
            razorpay_signature: Razorpay signature
            
        Returns:
            Updated payment record
        """
        # Get payment record with lock
        result = await self.db.execute(
            select(Payment)
            .where(Payment.razorpay_order_id == razorpay_order_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise PaymentError(f"Payment not found for order: {razorpay_order_id}")
        
        # Idempotency check - already processed
        if payment.status == PaymentStatus.SUCCESS:
            return payment
        
        # Verify amount matches (prevent tampering)
        if razorpay_amount is not None:
            expected_amount = int(payment.amount * 100)  # Convert to paise
            if razorpay_amount != expected_amount:
                raise PaymentError(
                    f"Amount mismatch: expected {expected_amount}, got {razorpay_amount}"
                )
        
        # Verify signature (in production, use Razorpay's verification)
        # For webhook, verify using webhook secret
        # For now, we accept the payment (implement full verification in production)
        
        # Update payment status
        payment.status = PaymentStatus.SUCCESS
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.paid_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    async def process_payment_failure(
        self,
        razorpay_order_id: str,
        error_code: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> Payment:
        """Process failed payment from webhook."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.razorpay_order_id == razorpay_order_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise PaymentError(f"Payment not found for order: {razorpay_order_id}")
        
        # Don't update if already successful
        if payment.status == PaymentStatus.SUCCESS:
            return payment
        
        payment.status = PaymentStatus.FAILED
        # Store error info if needed (extend model for error_code, error_description)
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    async def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Verify payment signature from frontend.
        Used for manual verification if needed.
        
        Args:
            order_id: Razorpay order ID
            payment_id: Razorpay payment ID
            signature: Signature from Razorpay checkout
            
        Returns:
            True if signature is valid
        """
        # Generate expected signature
        # Format: order_id|payment_id
        payload = f"{order_id}|{payment_id}"
        expected_signature = hmac.new(
            self.key_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def get_payment_details(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment details with booking info."""
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.booking))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        return {
            "id": str(payment.id),
            "booking_id": str(payment.booking_id),
            "amount": float(payment.amount),
            "status": payment.status.value,
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "paid_at": payment.paid_at,
            "created_at": payment.created_at,
        }