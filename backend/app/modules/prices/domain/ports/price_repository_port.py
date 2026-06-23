"""Contrato de acceso a precios vigentes e históricos del dominio."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.price import Price


class PriceRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para precios."""

    @abstractmethod
    async def get_by_id(self, price_id: UUID) -> Price | None:
        """Obtiene un precio por su identificador."""

    @abstractmethod
    async def find_current_by_product_source(self, product_source_id: UUID) -> list[Price]:
        """Busca precios vigentes para una publicación de producto."""

    @abstractmethod
    async def find_current_by_branch(self, branch_id: UUID) -> list[Price]:
        """Busca precios vigentes relevados en una sucursal."""

    @abstractmethod
    async def find_current_by_product_ids(self, product_ids: list[UUID]) -> list[Price]:
        """Busca precios vigentes para productos normalizados."""

    @abstractmethod
    async def find_for_basket(
        self,
        product_ids: list[UUID],
        branch_ids: list[UUID] | None = None,
    ) -> list[Price]:
        """Busca precios necesarios para calcular una canasta por sucursal."""

    @abstractmethod
    async def find_history(
        self,
        product_source_id: UUID,
        branch_id: UUID | None = None,
    ) -> list[Price]:
        """Obtiene el historial de precios de una publicación y sucursal opcional."""

    @abstractmethod
    async def save(self, price: Price) -> Price:
        """Guarda un precio y devuelve su representación de dominio."""

    @abstractmethod
    async def save_many(self, prices: list[Price]) -> list[Price]:
        """Guarda múltiples precios y devuelve sus representaciones de dominio."""
