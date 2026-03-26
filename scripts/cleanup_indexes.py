#!/usr/bin/env python3
"""Clean up orphaned indexes from failed table creation."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import engine


async def cleanup():
    """Drop orphaned indexes."""
    async with engine.begin() as conn:
        # Drop indexes if they exist
        await conn.execute(text("DROP INDEX IF EXISTS ix_password_reset_tokens_token"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_password_reset_tokens_user_id"))
        print("✅ Dropped orphaned indexes")


if __name__ == "__main__":
    print("🔧 Cleaning up orphaned indexes...")
    asyncio.run(cleanup())
    print("✨ Done!")