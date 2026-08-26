"""Schemas HTTP para consultas de precios."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PriceResponse(BaseModel):
    """Precio serializado para clientes HTTP."""

    id: UUID
    product_source_id: UUID
    product_id: UUID | None = None
    product_name: str | None = None
    product_source_name: str | None = None
    branch_id: UUID
    branch_name: str | None = None
    branch_address: str | None = None
    supermarket_id: UUID | None = None
    supermarket_name: str | None = None
    city_id: UUID | None = None
    city_name: str | None = None
    amount: Decimal
    currency: str
    observed_at: datetime
    available: bool
    promotion: bool
    quality_status: str
    quality_reason: str | None = None
    age_days: int
