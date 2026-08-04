"""Schemas HTTP del módulo de supermercados y localización."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CityResponse(BaseModel):
    """Ciudad serializada para clientes HTTP."""

    id: UUID
    province_id: UUID
    province_name: str | None = None
    name: str
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class SupermarketResponse(BaseModel):
    """Supermercado serializado para clientes HTTP."""

    id: UUID
    name: str
    website_url: str | None = None


class BranchResponse(BaseModel):
    """Sucursal serializada para clientes HTTP."""

    id: UUID
    supermarket_id: UUID
    supermarket_name: str | None = None
    city_id: UUID
    city_name: str | None = None
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
