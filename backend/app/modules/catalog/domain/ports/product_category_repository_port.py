"""Contrato de acceso a las categorías normalizadas del catálogo."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.product_category import ProductCategory


class ProductCategoryRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para categorías."""

    @abstractmethod
    async def get_by_id(self, category_id: UUID) -> ProductCategory | None:
        """Obtiene una categoría por su identificador."""

    @abstractmethod
    async def get_by_name(self, name: str) -> ProductCategory | None:
        """Obtiene una categoría por su nombre."""

    @abstractmethod
    async def list_active(self) -> list[ProductCategory]:
        """Lista las categorías activas."""

    @abstractmethod
    async def list_all(self) -> list[ProductCategory]:
        """Lista todas las categorías."""

    @abstractmethod
    async def save(self, category: ProductCategory) -> ProductCategory:
        """Guarda una categoría y devuelve su representación de dominio."""
