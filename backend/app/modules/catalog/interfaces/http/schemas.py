"""Schemas HTTP del módulo de catálogo."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ProductResponse(BaseModel):
    """Producto serializado para clientes HTTP."""

    id: UUID
    normalized_name: str
    category_id: UUID | None = None
    category_name: str | None = None
    brand_id: UUID | None = None
    brand_name: str | None = None
    description: str | None = None
    unit_measure: str | None = None
    net_content: Decimal | None = None
    internal_code: str | None = None


class ProductCategoryResponse(BaseModel):
    """Categoría serializada para clientes HTTP."""

    id: UUID
    name: str
    description: str | None = None
    parent_category_id: UUID | None = None


class BrandResponse(BaseModel):
    """Marca serializada para clientes HTTP."""

    id: UUID
    name: str
    description: str | None = None
