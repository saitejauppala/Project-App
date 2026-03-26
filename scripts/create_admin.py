#!/usr/bin/env python3
"""
Script to create admin user securely.
Run: python scripts/create_admin.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.database import async_session
from app.models.user import User, UserRole
from app.utils.security import get_password_hash


# Admin credentials - in production, load from environment variables
ADMIN_NAME = "Saiteja"
ADMIN_PHONE = "8333969325"
ADMIN_EMAIL = "saitejauppala07@gmail.com"
ADMIN_PASSWORD = "Saiteja@17"[:72]  # Truncate to bcrypt's 72-byte limit


async def create_admin_user():
    """Create admin user if not exists."""
    async with async_session() as db:
        try:
            # Check if admin already exists by phone
            result = await db.execute(
                select(User).where(User.phone == ADMIN_PHONE)
            )
            existing_by_phone = result.scalar_one_or_none()
            
            if existing_by_phone:
                if existing_by_phone.role == UserRole.ADMIN:
                    print(f"✅ Admin user already exists (phone: {ADMIN_PHONE})")
                    return
                else:
                    print(f"⚠️ User with phone {ADMIN_PHONE} exists but is not admin")
                    return
            
            # Check if admin already exists by email (if email field exists)
            # Note: Current User model doesn't have email, using phone as primary identifier
            
            # Create admin user
            admin_user = User(
                name=ADMIN_NAME,
                phone=ADMIN_PHONE,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            
            print(f"✅ Admin user created successfully!")
            print(f"   Name: {ADMIN_NAME}")
            print(f"   Phone: {ADMIN_PHONE}")
            print(f"   Role: {UserRole.ADMIN.value}")
            print(f"   User ID: {admin_user.id}")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating admin user: {e}")
            raise


if __name__ == "__main__":
    print("🔧 Creating admin user...")
    asyncio.run(create_admin_user())
    print("✨ Done!")