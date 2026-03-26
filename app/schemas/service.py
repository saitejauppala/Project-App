from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


# Service Category Schemas
class ServiceCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=255)


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class ServiceCategoryResponse(ServiceCategoryBase):
    id: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Service Schemas
class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Decimal = Field(..., gt=0, decimal_places=2)
    duration_minutes: int = Field(default=60, ge=15, le=480)


class ServiceCreate(ServiceBase):
    category_id: str


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    category_id: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: str
    category_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ServiceWithCategory(ServiceResponse):
    category: ServiceCategoryResponse


# Pagination Schemas
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int


class ServiceCategoryListResponse(PaginatedResponse):
    items: List[ServiceCategoryResponse]


class ServiceListResponse(PaginatedResponse):
    items: List[ServiceWithCategory]