"""Contrato de acceso a los productos normalizados del catálogo."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.product import Product


class ProductRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para productos."""

    @abstractmethod
    async def get_by_id(self, product_id: UUID) -> Product | None:
        """Obtiene un producto por su identificador."""

    @abstractmethod
    async def get_by_internal_code(self, internal_code: str) -> Product | None:
        """Obtiene un producto por su código interno."""

    @abstractmethod
    async def search_by_name(self, query: str, limit: int = 20) -> list[Product]:
        """Busca productos por nombre normalizado."""

    @abstractmethod
    async def list_active(self, limit: int = 100, offset: int = 0) -> list[Product]:
        """Lista productos activos usando paginación básica."""

    @abstractmethod
    async def save(self, product: Product) -> Product:
        """Guarda un producto y devuelve su representación de dominio."""
