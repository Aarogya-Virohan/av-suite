from __future__ import annotations

import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ClinicFeeItem(TimestampMixin, Base):
    __tablename__ = "clinic_fee_items"
    __table_args__ = (
        CheckConstraint("category IN ('consultation', 'posture', 'exercise_rx', 'custom')", name="ck_clinic_fee_items_category"),
        CheckConstraint("default_price >= 0", name="ck_clinic_fee_items_default_price_nonnegative"),
        Index("ix_clinic_fee_items_clinic_active_sort", "clinic_id", "active", "sort_order"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    default_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
