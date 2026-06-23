"""Adaptador SQLAlchemy asíncrono para el puerto de ciudades."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supermarkets.domain.entities import City
from app.modules.supermarkets.domain.ports import CityRepositoryPort

from .mappers import city_entity_to_model, city_model_to_entity
from .sqlalchemy_models import CityModel


class SQLAlchemyCityRepository(CityRepositoryPort):
    """Implementa el acceso a ciudades mediante una sesión SQLAlchemy asíncrona."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, city_id: UUID) -> City | None:
        """Obtiene una ciudad por identificador."""
        model = await self._session.get(CityModel, city_id)
        return city_model_to_entity(model) if model is not None else None

    async def list_by_province(self, province_id: UUID) -> list[City]:
        """Lista las ciudades de una provincia ordenadas por nombre."""
        models = await self._session.scalars(
            select(CityModel)
            .where(CityModel.provincia_id == province_id)
            .order_by(CityModel.nombre)
        )
        return [city_model_to_entity(model) for model in models.all()]

    async def list_all(self) -> list[City]:
        """Lista todas las ciudades ordenadas por nombre."""
        models = await self._session.scalars(select(CityModel).order_by(CityModel.nombre))
        return [city_model_to_entity(model) for model in models.all()]

    async def save(self, city: City) -> City:
        """Crea o actualiza una ciudad sin confirmar la transacción."""
        model = await self._session.get(CityModel, city.id)
        if model is None:
            model = city_entity_to_model(city)
            self._session.add(model)
        else:
            model.provincia_id = city.province_id
            model.nombre = city.name
            model.codigo_postal = city.postal_code
            model.latitud = city.latitude
            model.longitud = city.longitude

        await self._session.flush()
        return city_model_to_entity(model)
