#!/usr/bin/env python3
"""Full cleanup of password_reset_tokens table and all related objects."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import engine


async def full_cleanup():
    """Drop table and all indexes."""
    async with engine.begin() as conn:
        # Drop table (cascades indexes)
        await conn.execute(text("DROP TABLE IF EXISTS password_reset_tokens CASCADE"))
        print("✅ Dropped password_reset_tokens table")
        
        # Also drop any orphaned indexes just in case
        await conn.execute(text("DROP INDEX IF EXISTS ix_password_reset_tokens_token"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_password_reset_tokens_user_id"))
        print("✅ Dropped any orphaned indexes")


if __name__ == "__main__":
    print("🔧 Full cleanup of password_reset_tokens...")
    asyncio.run(full_cleanup())
    print("✨ Done! Table will be recreated on next app start.")