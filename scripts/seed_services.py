#!/usr/bin/env python3
"""
Seed script for EndlessPath service categories and services.
Based on actual registered providers from EPMS membership list.

Run: python scripts/seed_services.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.database import async_session
from app.models.service import ServiceCategory, Service


CATEGORIES = [
    {
        "name": "Automobile",
        "description": "Vehicle mechanic, car wash, and auto-repair services",
    },
    {
        "name": "Electrical & Electronics",
        "description": "AC repair, electrical wiring, and electronic device servicing",
    },
    {
        "name": "Transport & Rental",
        "description": "Car travels and self-drive car rental services",
    },
    {
        "name": "Beauty & Wellness",
        "description": "Mehendi and personal care services",
    },
    {
        "name": "Real Estate",
        "description": "Property buying, selling, and rental consultation",
    },
    {
        "name": "Food & Catering",
        "description": "Biryani, catering, and food delivery services",
    },
]


# duration_minutes = duration_hours * 60
SERVICES = [
    # Automobile
    {
        "category": "Automobile",
        "name": "Vehicle Mechanic",
        "description": "Professional vehicle mechanic for all types of repairs and maintenance",
        "base_price": 299.0,
        "duration_minutes": 120,
        "service_code": "EPMS001",
    },
    {
        "category": "Automobile",
        "name": "Car Wash",
        "description": "Professional car cleaning and washing service at your doorstep",
        "base_price": 199.0,
        "duration_minutes": 60,
        "service_code": "EPMS006",
    },
    # Electrical & Electronics
    {
        "category": "Electrical & Electronics",
        "name": "AC & Electrical Works",
        "description": "AC servicing, repair, and general electrical work",
        "base_price": 399.0,
        "duration_minutes": 120,
        "service_code": "EPMS002",
    },
    {
        "category": "Electrical & Electronics",
        "name": "Electrical Works",
        "description": "Home and commercial electrical wiring, fitting, and repairs",
        "base_price": 349.0,
        "duration_minutes": 120,
        "service_code": "EPMS003",
    },
    {
        "category": "Electrical & Electronics",
        "name": "Electronic Shop & Repair",
        "description": "Electronic device repair and servicing",
        "base_price": 249.0,
        "duration_minutes": 60,
        "service_code": "EPMS004",
    },
    # Transport & Rental
    {
        "category": "Transport & Rental",
        "name": "Car Travels",
        "description": "Comfortable car travel service for outstation and local trips",
        "base_price": 999.0,
        "duration_minutes": 240,
        "service_code": "EPMS005",
    },
    {
        "category": "Transport & Rental",
        "name": "Self Drive Car Rental",
        "description": "Self-drive car rental with flexible hourly and daily packages",
        "base_price": 799.0,
        "duration_minutes": 480,
        "service_code": "EPMS009",
    },
    # Beauty & Wellness
    {
        "category": "Beauty & Wellness",
        "name": "Mehendi / Bridal Henna",
        "description": "Professional mehendi designs for weddings and special occasions",
        "base_price": 299.0,
        "duration_minutes": 120,
        "service_code": "EPMS007",
    },
    # Real Estate
    {
        "category": "Real Estate",
        "name": "Real Estate Consultation",
        "description": "Property buying, selling, rental, and investment consultation",
        "base_price": 499.0,
        "duration_minutes": 60,
        "service_code": "EPMS008",
    },
    # Food & Catering
    {
        "category": "Food & Catering",
        "name": "Biryani & Catering",
        "description": "Fresh biryani and catering services for events and bulk orders",
        "base_price": 349.0,
        "duration_minutes": 60,
        "service_code": "EPMS010",
    },
]


async def seed():
    async with async_session() as db:
        try:
            created_categories = 0
            created_services = 0
            category_map = {}

            print("📂 Seeding service categories...\n")
            for cat_data in CATEGORIES:
                result = await db.execute(
                    select(ServiceCategory).where(ServiceCategory.name == cat_data["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  ⏩ Exists: {cat_data['name']}")
                    category_map[cat_data["name"]] = existing
                else:
                    category = ServiceCategory(
                        name=cat_data["name"],
                        description=cat_data["description"],
                    )
                    db.add(category)
                    await db.flush()
                    category_map[cat_data["name"]] = category
                    created_categories += 1
                    print(f"  ✅ Created: {cat_data['name']}")

            print("\n🛠️  Seeding services...\n")
            for svc in SERVICES:
                result = await db.execute(
                    select(Service).where(Service.name == svc["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  ⏩ Exists: {svc['name']}")
                    continue

                category = category_map.get(svc["category"])
                if not category:
                    print(f"  ❌ Category not found: {svc['category']}")
                    continue

                service = Service(
                    category_id=category.id,
                    name=svc["name"],
                    description=svc["description"],
                    base_price=svc["base_price"],
                    duration_minutes=svc["duration_minutes"],
                    is_active=True,
                )
                db.add(service)
                created_services += 1
                print(
                    f"  ✅ [{svc['service_code']}] {svc['name']} "
                    f"- ₹{svc['base_price']} ({svc['duration_minutes']} min)"
                )

            await db.commit()

            print(f"\n🎉 Done!")
            print(f"   Categories created : {created_categories}")
            print(f"   Services created   : {created_services}")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error: {e}")
            raise


if __name__ == "__main__":
    print("🌱 EndlessPath Service Seeder\n" + "=" * 40 + "\n")
    asyncio.run(seed())
