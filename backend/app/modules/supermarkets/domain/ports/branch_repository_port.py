"""Contrato de acceso a las entidades de sucursal del dominio."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.branch import Branch


class BranchRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para sucursales."""

    @abstractmethod
    async def get_by_id(self, branch_id: UUID) -> Branch | None:
        """Obtiene una sucursal por su identificador."""

    @abstractmethod
    async def list_active(self) -> list[Branch]:
        """Lista las sucursales activas sin calcular cercanía."""

    @abstractmethod
    async def list_by_supermarket(self, supermarket_id: UUID) -> list[Branch]:
        """Lista las sucursales pertenecientes a un supermercado."""

    @abstractmethod
    async def list_by_city(self, city_id: UUID) -> list[Branch]:
        """Lista las sucursales ubicadas en una ciudad."""

    @abstractmethod
    async def save(self, branch: Branch) -> Branch:
        """Guarda una sucursal y devuelve su representación de dominio."""
