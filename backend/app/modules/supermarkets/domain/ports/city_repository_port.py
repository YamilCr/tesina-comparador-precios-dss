"""Contrato de acceso a las entidades de ciudad del dominio."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..entities.city import City


class CityRepositoryPort(ABC):
    """Define las operaciones de persistencia requeridas para ciudades."""

    @abstractmethod
    async def get_by_id(self, city_id: UUID) -> City | None:
        """Obtiene una ciudad por su identificador."""

    @abstractmethod
    async def list_by_province(self, province_id: UUID) -> list[City]:
        """Lista las ciudades que pertenecen a una provincia."""

    @abstractmethod
    async def list_all(self) -> list[City]:
        """Lista todas las ciudades disponibles."""

    @abstractmethod
    async def save(self, city: City) -> City:
        """Guarda una ciudad y devuelve su representación de dominio."""
