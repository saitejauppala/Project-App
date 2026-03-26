from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import ServiceCategory, Service
from app.schemas.service import (
    ServiceCategoryCreate, ServiceCategoryUpdate,
    ServiceCreate, ServiceUpdate, PaginationParams
)


class ServiceCategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, category_id: str) -> Optional[ServiceCategory]:
        """Get category by ID."""
        result = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[ServiceCategory]:
        """Get category by name (case-insensitive)."""
        result = await self.db.execute(
            select(ServiceCategory).where(
                func.lower(ServiceCategory.name) == func.lower(name)
            )
        )
        return result.scalar_one_or_none()

    async def check_name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if category name already exists."""
        query = select(ServiceCategory).where(
            func.lower(ServiceCategory.name) == func.lower(name)
        )
        if exclude_id:
            query = query.where(ServiceCategory.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_all(
        self, pagination: PaginationParams, only_active: bool = True
    ) -> Tuple[List[ServiceCategory], int]:
        """Get all categories with pagination."""
        query = select(ServiceCategory)
        if only_active:
            query = query.where(ServiceCategory.is_active == True)
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Get paginated results
        query = query.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def create(self, category_data: ServiceCategoryCreate) -> ServiceCategory:
        """Create a new category."""
        if await self.check_name_exists(category_data.name):
            raise ValueError(f"Category with name '{category_data.name}' already exists")
        
        db_category = ServiceCategory(
            name=category_data.name,
            description=category_data.description,
            icon=category_data.icon,
            is_active=True,
        )
        self.db.add(db_category)
        await self.db.commit()
        await self.db.refresh(db_category)
        return db_category

    async def update(
        self, category_id: str, category_data: ServiceCategoryUpdate
    ) -> Optional[ServiceCategory]:
        """Update a category."""
        category = await self.get_by_id(category_id)
        if not category:
            return None
        
        # Check name uniqueness if updating name
        if category_data.name and category_data.name != category.name:
            if await self.check_name_exists(category_data.name, exclude_id=category_id):
                raise ValueError(f"Category with name '{category_data.name}' already exists")
            category.name = category_data.name
        
        if category_data.description is not None:
            category.description = category_data.description
        if category_data.icon is not None:
            category.icon = category_data.icon
        if category_data.is_active is not None:
            category.is_active = category_data.is_active
        
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: str) -> bool:
        """Soft delete a category (deactivate)."""
        category = await self.get_by_id(category_id)
        if not category:
            return False
        
        category.is_active = False
        await self.db.commit()
        return True


class ServiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, service_id: str) -> Optional[Service]:
        """Get service by ID."""
        result = await self.db.execute(
            select(Service).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        pagination: PaginationParams,
        category_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        only_active: bool = True,
    ) -> Tuple[List[Service], int]:
        """Get all services with optional filtering and pagination."""
        query = select(Service)
        
        if only_active:
            query = query.where(Service.is_active == True)
        
        if category_id:
            query = query.where(Service.category_id == category_id)

        if provider_id:
            query = query.where(Service.provider_id == provider_id)
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Get paginated results with category
        query = (
            query.offset((pagination.page - 1) * pagination.limit)
            .limit(pagination.limit)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def get_by_category(self, category_id: str, pagination: PaginationParams) -> Tuple[List[Service], int]:
        """Get services by category."""
        return await self.get_all(pagination, category_id=category_id)

    async def create(self, service_data: ServiceCreate) -> Service:
        """Create a new service."""
        db_service = Service(
            name=service_data.name,
            description=service_data.description,
            base_price=service_data.base_price,
            duration_minutes=service_data.duration_minutes,
            category_id=service_data.category_id,
            is_active=True,
        )
        self.db.add(db_service)
        await self.db.commit()
        await self.db.refresh(db_service)
        return db_service

    async def update(self, service_id: str, service_data: ServiceUpdate) -> Optional[Service]:
        """Update a service."""
        service = await self.get_by_id(service_id)
        if not service:
            return None
        
        update_fields = {
            "name": service_data.name,
            "description": service_data.description,
            "base_price": service_data.base_price,
            "duration_minutes": service_data.duration_minutes,
            "category_id": service_data.category_id,
            "is_active": service_data.is_active,
        }
        
        for field, value in update_fields.items():
            if value is not None:
                setattr(service, field, value)
        
        await self.db.commit()
        await self.db.refresh(service)
        return service

    async def delete(self, service_id: str) -> bool:
        """Soft delete a service (deactivate)."""
        service = await self.get_by_id(service_id)
        if not service:
            return False
        
        service.is_active = False
        await self.db.commit()
        return True