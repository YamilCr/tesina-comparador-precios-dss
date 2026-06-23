"""Contrato de acceso a las entidades de supermercado del dominio."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.supermarket import Supermarket


class SupermarketRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para supermercados."""

    @abstractmethod
    async def get_by_id(self, supermarket_id: UUID) -> Supermarket | None:
        """Obtiene un supermercado por su identificador."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Supermarket | None:
        """Obtiene un supermercado por su nombre."""

    @abstractmethod
    async def list_active(self) -> list[Supermarket]:
        """Lista los supermercados activos."""

    @abstractmethod
    async def list_all(self) -> list[Supermarket]:
        """Lista todos los supermercados."""

    @abstractmethod
    async def save(self, supermarket: Supermarket) -> Supermarket:
        """Guarda un supermercado y devuelve su representación de dominio."""
