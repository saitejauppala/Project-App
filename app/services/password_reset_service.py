"""Password reset service with secure token generation."""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.password_reset import PasswordResetToken


class PasswordResetError(Exception):
    """Password reset specific errors."""
    pass


class PasswordResetService:
    """Service for handling password reset operations."""
    
    TOKEN_EXPIRY_MINUTES = 15
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_user_by_email_or_phone(self, email_or_phone: str) -> Optional[User]:
        """Find user by email or phone."""
        # Try phone first (primary identifier in this system)
        result = await self.db.execute(
            select(User).where(User.phone == email_or_phone)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return user
        
        # Note: If email field is added to User model, search by email here
        # For now, phone is the primary identifier
        
        return None
    
    def _generate_secure_token(self) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(32)
    
    async def create_reset_token(self, user_id: str) -> PasswordResetToken:
        """Create a new password reset token for a user."""
        token = self._generate_secure_token()
        expires_at = datetime.utcnow() + timedelta(minutes=self.TOKEN_EXPIRY_MINUTES)
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_used=False,
        )
        
        self.db.add(reset_token)
        await self.db.commit()
        await self.db.refresh(reset_token)
        
        return reset_token
    
    async def request_password_reset(self, email_or_phone: str) -> Optional[str]:
        """
        Request password reset.
        
        Returns token if user found, None otherwise.
        Always returns generic success to prevent user enumeration.
        """
        user = await self.find_user_by_email_or_phone(email_or_phone)
        
        if not user:
            # Return None but don't expose that user doesn't exist
            return None
        
        # Create reset token
        reset_token = await self.create_reset_token(str(user.id))
        
        return reset_token.token
    
    async def validate_token(self, token: str) -> Optional[PasswordResetToken]:
        """Validate a reset token."""
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        reset_token = result.scalar_one_or_none()
        
        if not reset_token:
            return None
        
        # Check if token is used
        if reset_token.is_used:
            return None
        
        # Check if token is expired
        if datetime.utcnow() > reset_token.expires_at:
            return None
        
        return reset_token
    
    async def mark_token_used(self, reset_token: PasswordResetToken) -> None:
        """Mark a token as used."""
        reset_token.is_used = True
        await self.db.commit()