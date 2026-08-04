"""Caso de uso para listar ciudades disponibles."""

from app.modules.supermarkets.application.dto import CityDTO
from app.shared.application import UnitOfWorkPort


class ListCitiesUseCase:
    """Lista ciudades sin acoplarse a consultas SQL concretas."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self) -> list[CityDTO]:
        """Obtiene todas las ciudades registradas."""
        async with self._uow as uow:
            cities = await uow.cities.list_all()
            return [CityDTO.from_entity(city) for city in cities]
