"""Adaptador SQLAlchemy asíncrono para el puerto de provincias."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supermarkets.domain.entities import Province
from app.modules.supermarkets.domain.ports import ProvinceRepositoryPort

from .mappers import province_entity_to_model, province_model_to_entity
from .sqlalchemy_models import ProvinceModel


class SQLAlchemyProvinceRepository(ProvinceRepositoryPort):
    """Implementa el acceso a provincias mediante una sesión SQLAlchemy asíncrona."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, province_id: UUID) -> Province | None:
        """Obtiene una provincia por identificador."""
        model = await self._session.get(ProvinceModel, province_id)
        return province_model_to_entity(model) if model is not None else None

    async def get_by_name(self, name: str) -> Province | None:
        """Obtiene una provincia por nombre."""
        model = await self._session.scalar(
            select(ProvinceModel).where(ProvinceModel.nombre == name)
        )
        return province_model_to_entity(model) if model is not None else None

    async def list_all(self) -> list[Province]:
        """Lista todas las provincias ordenadas por nombre."""
        models = await self._session.scalars(select(ProvinceModel).order_by(ProvinceModel.nombre))
        return [province_model_to_entity(model) for model in models.all()]

    async def save(self, province: Province) -> Province:
        """Crea o actualiza una provincia sin confirmar la transacción."""
        model = await self._session.get(ProvinceModel, province.id)
        if model is None:
            model = province_entity_to_model(province)
            self._session.add(model)
        else:
            model.nombre = province.name
            model.codigo_iso = province.iso_code
            if province.created_at is not None:
                model.created_at = province.created_at

        await self._session.flush()
        return province_model_to_entity(model)
