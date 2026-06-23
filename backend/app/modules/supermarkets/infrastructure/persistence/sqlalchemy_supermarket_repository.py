"""Adaptador SQLAlchemy asíncrono para el puerto de supermercados."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supermarkets.domain.entities import Supermarket
from app.modules.supermarkets.domain.ports import SupermarketRepositoryPort

from .mappers import supermarket_entity_to_model, supermarket_model_to_entity
from .sqlalchemy_models import SupermarketModel


class SQLAlchemySupermarketRepository(SupermarketRepositoryPort):
    """Implementa el acceso a supermercados mediante SQLAlchemy asíncrono."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, supermarket_id: UUID) -> Supermarket | None:
        """Obtiene un supermercado por identificador."""
        model = await self._session.get(SupermarketModel, supermarket_id)
        return supermarket_model_to_entity(model) if model is not None else None

    async def get_by_name(self, name: str) -> Supermarket | None:
        """Obtiene un supermercado por nombre."""
        model = await self._session.scalar(
            select(SupermarketModel).where(SupermarketModel.nombre == name)
        )
        return supermarket_model_to_entity(model) if model is not None else None

    async def list_active(self) -> list[Supermarket]:
        """Lista los supermercados activos ordenados por nombre."""
        models = await self._session.scalars(
            select(SupermarketModel)
            .where(SupermarketModel.activo.is_(True))
            .order_by(SupermarketModel.nombre)
        )
        return [supermarket_model_to_entity(model) for model in models.all()]

    async def list_all(self) -> list[Supermarket]:
        """Lista todos los supermercados ordenados por nombre."""
        models = await self._session.scalars(
            select(SupermarketModel).order_by(SupermarketModel.nombre)
        )
        return [supermarket_model_to_entity(model) for model in models.all()]

    async def save(self, supermarket: Supermarket) -> Supermarket:
        """Crea o actualiza un supermercado sin confirmar la transacción."""
        model = await self._session.get(SupermarketModel, supermarket.id)
        if model is None:
            model = supermarket_entity_to_model(supermarket)
            self._session.add(model)
        else:
            model.nombre = supermarket.name
            model.sitio_web = supermarket.website_url
            model.activo = supermarket.active
            if supermarket.created_at is not None:
                model.created_at = supermarket.created_at

        await self._session.flush()
        return supermarket_model_to_entity(model)
