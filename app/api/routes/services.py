from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.redis import redis_client, cached
from app.schemas.service import (
    ServiceCategoryCreate, ServiceCategoryUpdate, ServiceCategoryResponse,
    ServiceCategoryListResponse,
    ServiceCreate, ServiceUpdate, ServiceResponse, ServiceWithCategory,
    ServiceListResponse, PaginationParams,
)
from app.services.service_service import ServiceCategoryService, ServiceService

router = APIRouter(prefix="/services", tags=["Services"])


# ============== CATEGORY ENDPOINTS ==============

@router.get("/categories", response_model=ServiceCategoryListResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all service categories (public endpoint, cached for 5 minutes)."""
    # Try cache first
    cache_key = f"categories:list:{page}:{limit}"
    cached_result = await redis_client.get(cache_key)
    
    if cached_result:
        import json
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            pass
    
    pagination = PaginationParams(page=page, limit=limit)
    category_service = ServiceCategoryService(db)
    
    items, total = await category_service.get_all(pagination)
    pages = (total + limit - 1) // limit
    
    result = ServiceCategoryListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )
    
    # Cache result
    try:
        await redis_client.set(cache_key, result.model_dump_json(), expire=300)
    except Exception:
        pass
    
    return result


@router.get("/categories/{category_id}", response_model=ServiceCategoryResponse)
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific category by ID."""
    category_service = ServiceCategoryService(db)
    category = await category_service.get_by_id(category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return category


@router.post(
    "/categories",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    category_data: ServiceCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Create a new category (admin only)."""
    category_service = ServiceCategoryService(db)
    
    try:
        category = await category_service.create(category_data)
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/categories/{category_id}", response_model=ServiceCategoryResponse)
async def update_category(
    category_id: str,
    category_data: ServiceCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Update a category (admin only)."""
    category_service = ServiceCategoryService(db)
    
    try:
        category = await category_service.update(category_id, category_data)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Soft delete a category (admin only)."""
    category_service = ServiceCategoryService(db)
    
    deleted = await category_service.delete(category_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    
    return None


# ============== SERVICE ENDPOINTS ==============

@router.get("/", response_model=ServiceListResponse)
async def list_services(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all services with optional category filter (public endpoint, cached for 5 minutes)."""
    # Try cache first
    cache_key = f"services:list:{page}:{limit}:{category_id or 'all'}"
    cached_result = await redis_client.get(cache_key)
    
    if cached_result:
        import json
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            pass
    
    pagination = PaginationParams(page=page, limit=limit)
    service_service = ServiceService(db)
    
    items, total = await service_service.get_all(
        pagination, category_id=category_id
    )
    pages = (total + limit - 1) // limit
    
    result = ServiceListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )
    
    # Cache result
    try:
        await redis_client.set(cache_key, result.model_dump_json(), expire=300)
    except Exception:
        pass
    
    return result


@router.get("/{service_id}", response_model=ServiceWithCategory)
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific service by ID."""
    service_service = ServiceService(db)
    service = await service_service.get_by_id(service_id)
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    return service


@router.post(
    "/",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service(
    service_data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Create a new service (admin only)."""
    service_service = ServiceService(db)
    category_service = ServiceCategoryService(db)
    
    # Verify category exists
    category = await category_service.get_by_id(service_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )
    
    service = await service_service.create(service_data)
    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    service_data: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Update a service (admin only)."""
    service_service = ServiceService(db)
    
    # If category_id is being updated, verify it exists
    if service_data.category_id:
        category_service = ServiceCategoryService(db)
        category = await category_service.get_by_id(service_data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found",
            )
    
    service = await service_service.update(service_id, service_data)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Soft delete a service (admin only)."""
    service_service = ServiceService(db)
    
    deleted = await service_service.delete(service_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    return None