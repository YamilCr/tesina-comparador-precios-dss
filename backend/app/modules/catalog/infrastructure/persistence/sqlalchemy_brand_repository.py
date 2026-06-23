"""Adaptador SQLAlchemy asíncrono para el puerto de marcas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.entities import Brand
from app.modules.catalog.domain.ports import BrandRepositoryPort

from .mappers import brand_entity_to_model, brand_model_to_entity
from .sqlalchemy_models import BrandModel


class SQLAlchemyBrandRepository(BrandRepositoryPort):
    """Implementa el acceso a marcas mediante una sesión SQLAlchemy asíncrona."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, brand_id: UUID) -> Brand | None:
        """Obtiene una marca por identificador."""
        model = await self._session.get(BrandModel, brand_id)
        return brand_model_to_entity(model) if model is not None else None

    async def get_by_name(self, name: str) -> Brand | None:
        """Obtiene una marca por nombre."""
        model = await self._session.scalar(select(BrandModel).where(BrandModel.nombre == name))
        return brand_model_to_entity(model) if model is not None else None

    async def list_active(self) -> list[Brand]:
        """Lista las marcas activas ordenadas por nombre."""
        models = await self._session.scalars(
            select(BrandModel).where(BrandModel.activo.is_(True)).order_by(BrandModel.nombre)
        )
        return [brand_model_to_entity(model) for model in models.all()]

    async def list_all(self) -> list[Brand]:
        """Lista todas las marcas ordenadas por nombre."""
        models = await self._session.scalars(select(BrandModel).order_by(BrandModel.nombre))
        return [brand_model_to_entity(model) for model in models.all()]

    async def save(self, brand: Brand) -> Brand:
        """Crea o actualiza una marca sin confirmar la transacción."""
        model = await self._session.get(BrandModel, brand.id)
        if model is None:
            model = brand_entity_to_model(brand)
            self._session.add(model)
        else:
            model.nombre = brand.name
            model.descripcion = brand.description
            model.activo = brand.active

        await self._session.flush()
        return brand_model_to_entity(model)
