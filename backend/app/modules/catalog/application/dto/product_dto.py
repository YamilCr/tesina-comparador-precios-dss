"""DTO de aplicación para productos normalizados del catálogo."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.catalog.domain.entities import Product


@dataclass(frozen=True)
class ProductDTO:
    """Producto normalizado expuesto por la capa de aplicación."""

    id: UUID
    normalized_name: str
    category_id: UUID | None = None
    brand_id: UUID | None = None
    description: str | None = None
    unit_measure: str | None = None
    net_content: Decimal | None = None
    internal_code: str | None = None
    active: bool = True

    @staticmethod
    def from_entity(product: Product) -> "ProductDTO":
        """Crea un DTO desde una entidad de dominio Product."""
        return ProductDTO(
            id=product.id,
            normalized_name=product.normalized_name,
            category_id=product.category_id,
            brand_id=product.brand_id,
            description=product.description,
            unit_measure=product.unit_measure,
            net_content=product.net_content,
            internal_code=product.internal_code,
            active=product.active,
        )
