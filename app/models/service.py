import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Text, Numeric, ForeignKey, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    services: Mapped[List["Service"]] = relationship("Service", back_populates="category")

    def __repr__(self) -> str:
        return f"<ServiceCategory(id={self.id}, name={self.name})>"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="CASCADE"), nullable=False
    )
    # Provider who owns this service listing (nullable = global/admin-created service)
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    category: Mapped["ServiceCategory"] = relationship("ServiceCategory", back_populates="services")
    provider: Mapped[Optional["User"]] = relationship("User", foreign_keys=[provider_id])
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="service")

    # Indexes
    __table_args__ = (
        Index("idx_service_category_active", "category_id", "is_active"),
        Index("idx_service_provider", "provider_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, price={self.base_price})>"