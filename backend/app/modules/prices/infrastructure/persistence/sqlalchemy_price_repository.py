"""Adaptador SQLAlchemy asíncrono para el puerto de precios."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.infrastructure.persistence.sqlalchemy_models import ProductSourceModel
from app.modules.prices.domain.entities import Price
from app.modules.prices.domain.ports import PriceRepositoryPort

from .mappers import price_entity_to_model, price_model_to_entity
from .sqlalchemy_models import PriceModel


class SQLAlchemyPriceRepository(PriceRepositoryPort):
    """Implementa consultas y guardado de precios usando SQLAlchemy asíncrono."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, price_id: UUID) -> Price | None:
        """Obtiene un precio por identificador."""
        model = await self._session.get(PriceModel, price_id)
        return price_model_to_entity(model) if model is not None else None

    async def find_current_by_product_source(self, product_source_id: UUID) -> list[Price]:
        """Busca precios disponibles de una publicación, recientes primero."""
        models = await self._session.scalars(
            select(PriceModel)
            .where(
                PriceModel.producto_fuente_id == product_source_id,
                PriceModel.disponible.is_(True),
            )
            .order_by(PriceModel.fecha_relevamiento.desc())
        )
        return [price_model_to_entity(model) for model in models.all()]

    async def find_current_by_branch(self, branch_id: UUID) -> list[Price]:
        """Busca precios disponibles de una sucursal, recientes primero."""
        models = await self._session.scalars(
            select(PriceModel)
            .where(
                PriceModel.sucursal_id == branch_id,
                PriceModel.disponible.is_(True),
            )
            .order_by(PriceModel.fecha_relevamiento.desc())
        )
        return [price_model_to_entity(model) for model in models.all()]

    async def find_current_by_product_ids(self, product_ids: list[UUID]) -> list[Price]:
        """Busca precios disponibles a través de productos y sus publicaciones."""
        if not product_ids:
            return []

        models = await self._session.scalars(
            select(PriceModel)
            .join(ProductSourceModel, PriceModel.producto_fuente_id == ProductSourceModel.id)
            .where(
                ProductSourceModel.producto_id.in_(product_ids),
                PriceModel.disponible.is_(True),
            )
            .order_by(PriceModel.fecha_relevamiento.desc())
        )
        return [price_model_to_entity(model) for model in models.all()]

    async def find_for_basket(
        self,
        product_ids: list[UUID],
        branch_ids: list[UUID] | None = None,
    ) -> list[Price]:
        """Busca precios disponibles para productos de una canasta temporal."""
        if not product_ids:
            return []

        statement = (
            select(PriceModel)
            .join(ProductSourceModel, PriceModel.producto_fuente_id == ProductSourceModel.id)
            .where(
                ProductSourceModel.producto_id.in_(product_ids),
                PriceModel.disponible.is_(True),
            )
            .order_by(PriceModel.sucursal_id, PriceModel.fecha_relevamiento.desc())
        )
        if branch_ids is not None:
            if not branch_ids:
                return []
            statement = statement.where(PriceModel.sucursal_id.in_(branch_ids))

        models = await self._session.scalars(statement)
        return [price_model_to_entity(model) for model in models.all()]

    async def find_history(
        self,
        product_source_id: UUID,
        branch_id: UUID | None = None,
    ) -> list[Price]:
        """Obtiene histórico de precios, filtrado opcionalmente por sucursal."""
        statement = (
            select(PriceModel)
            .where(PriceModel.producto_fuente_id == product_source_id)
            .order_by(PriceModel.fecha_relevamiento.desc())
        )
        if branch_id is not None:
            statement = statement.where(PriceModel.sucursal_id == branch_id)

        models = await self._session.scalars(statement)
        return [price_model_to_entity(model) for model in models.all()]

    async def save(self, price: Price) -> Price:
        """Crea o actualiza un precio sin confirmar la transacción."""
        model = await self._session.get(PriceModel, price.id)
        if model is None:
            model = price_entity_to_model(price)
            self._session.add(model)
        else:
            model.producto_fuente_id = price.product_source_id
            model.sucursal_id = price.branch_id
            model.precio = price.amount
            model.moneda = price.currency
            model.fecha_relevamiento = price.observed_at
            model.disponible = price.available
            model.promocion = price.promotion
            if price.created_at is not None:
                model.created_at = price.created_at

        await self._session.flush()
        return price_model_to_entity(model)

    async def save_many(self, prices: list[Price]) -> list[Price]:
        """Guarda múltiples precios sin confirmar la transacción."""
        return [await self.save(price) for price in prices]
