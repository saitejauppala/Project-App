from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, ProviderProfile, UserRole
from app.utils.security import get_password_hash, verify_password
from app.schemas.user import UserRegister, ProviderProfileCreate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def check_phone_exists(self, phone: str) -> bool:
        """Check if phone number already exists."""
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none() is not None

    async def create_user(self, user_data: UserRegister) -> User:
        """Create a new user."""
        # Check if phone already exists
        if await self.check_phone_exists(user_data.phone):
            raise ValueError("Phone number already registered")
        
        # Create user
        db_user = User(
            name=user_data.name,
            phone=user_data.phone,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        self.db.add(db_user)
        await self.db.flush()  # Flush to get the user ID
        
        # Create provider profile if role is provider
        if user_data.role == UserRole.PROVIDER:
            provider_profile = ProviderProfile(
                user_id=db_user.id,
                skills=[],
                rating=0.0,
                total_reviews=0,
                is_available=True,
                is_verified=False,
            )
            self.db.add(provider_profile)
        
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def authenticate(self, phone: str, password: str) -> Optional[User]:
        """Authenticate user with phone and password."""
        user = await self.get_by_phone(phone)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    async def update_provider_profile(
        self, user_id: str, profile_data: ProviderProfileCreate
    ) -> Optional[ProviderProfile]:
        """Update provider profile."""
        result = await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return None
        
        if profile_data.skills is not None:
            profile.skills = profile_data.skills
        if profile_data.bio is not None:
            profile.bio = profile_data.bio
        
        await self.db.commit()
        await self.db.refresh(profile)
        return profile