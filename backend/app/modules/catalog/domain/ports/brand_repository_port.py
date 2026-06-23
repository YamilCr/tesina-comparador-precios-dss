"""Contrato de acceso a las marcas normalizadas del catálogo."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.brand import Brand


class BrandRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para marcas."""

    @abstractmethod
    async def get_by_id(self, brand_id: UUID) -> Brand | None:
        """Obtiene una marca por su identificador."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Brand | None:
        """Obtiene una marca por su nombre."""

    @abstractmethod
    async def list_active(self) -> list[Brand]:
        """Lista las marcas activas."""

    @abstractmethod
    async def list_all(self) -> list[Brand]:
        """Lista todas las marcas."""

    @abstractmethod
    async def save(self, brand: Brand) -> Brand:
        """Guarda una marca y devuelve su representación de dominio."""
