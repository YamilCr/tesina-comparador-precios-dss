"""DTO de aplicación para categorías de productos."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.catalog.domain.entities import ProductCategory


@dataclass(frozen=True)
class ProductCategoryDTO:
    """Categoría normalizada expuesta por la capa de aplicación."""

    id: UUID
    name: str
    description: str | None = None
    parent_category_id: UUID | None = None
    active: bool = True

    @staticmethod
    def from_entity(category: ProductCategory) -> "ProductCategoryDTO":
        """Crea un DTO desde una entidad de dominio ProductCategory."""
        return ProductCategoryDTO(
            id=category.id,
            name=category.name,
            description=category.description,
            parent_category_id=category.parent_category_id,
            active=category.active,
        )
