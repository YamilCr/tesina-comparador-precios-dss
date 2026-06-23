"""Contrato de acceso a productos publicados por fuentes externas."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.product_source import ProductSource


class ProductSourceRepositoryPort(ABC):
    """Define el acceso a publicaciones de productos por supermercado."""

    @abstractmethod
    async def get_by_id(self, product_source_id: UUID) -> ProductSource | None:
        """Obtiene una fuente de producto por su identificador."""

    @abstractmethod
    async def find_by_product(self, product_id: UUID) -> list[ProductSource]:
        """Busca publicaciones asociadas a un producto normalizado."""

    @abstractmethod
    async def find_by_supermarket(self, supermarket_id: UUID) -> list[ProductSource]:
        """Busca publicaciones pertenecientes a un supermercado."""

    @abstractmethod
    async def find_by_external_code(
        self,
        supermarket_id: UUID,
        external_code: str,
    ) -> ProductSource | None:
        """Busca una publicación por supermercado y código externo."""

    @abstractmethod
    async def save(self, product_source: ProductSource) -> ProductSource:
        """Guarda una publicación y devuelve su representación de dominio."""

    @abstractmethod
    async def save_many(self, product_sources: list[ProductSource]) -> list[ProductSource]:
        """Guarda múltiples publicaciones y devuelve sus representaciones de dominio."""
