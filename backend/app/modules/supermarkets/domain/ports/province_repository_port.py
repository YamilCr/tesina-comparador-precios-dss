"""Contrato de acceso a las entidades de provincia del dominio."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.province import Province


class ProvinceRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para provincias."""

    @abstractmethod
    async def get_by_id(self, province_id: UUID) -> Province | None:
        """Obtiene una provincia por su identificador."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Province | None:
        """Obtiene una provincia por su nombre."""

    @abstractmethod
    async def list_all(self) -> list[Province]:
        """Lista todas las provincias disponibles."""

    @abstractmethod
    async def save(self, province: Province) -> Province:
        """Guarda una provincia y devuelve su representación de dominio."""
