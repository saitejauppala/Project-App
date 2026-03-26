#!/usr/bin/env python3
"""
Script to drop password_reset_tokens table if it exists.
Run this if the table was created with wrong schema.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import async_session, engine


async def drop_table():
    """Drop password_reset_tokens table if exists."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS password_reset_tokens CASCADE"))
        print("✅ Dropped password_reset_tokens table if it existed")


if __name__ == "__main__":
    print("🔧 Cleaning up password_reset_tokens table...")
    asyncio.run(drop_table())
    print("✨ Done! Restart the app to recreate the table with correct schema.")