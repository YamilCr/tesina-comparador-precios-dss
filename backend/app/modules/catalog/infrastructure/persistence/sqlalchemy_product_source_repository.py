"""Adaptador SQLAlchemy asíncrono para el puerto de productos fuente."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.entities import ProductSource
from app.modules.catalog.domain.ports import ProductSourceRepositoryPort

from .mappers import product_source_entity_to_model, product_source_model_to_entity
from .sqlalchemy_models import ProductSourceModel


class SQLAlchemyProductSourceRepository(ProductSourceRepositoryPort):
    """Implementa el acceso a publicaciones por supermercado mediante SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, product_source_id: UUID) -> ProductSource | None:
        """Obtiene una publicación por identificador."""
        model = await self._session.get(ProductSourceModel, product_source_id)
        return product_source_model_to_entity(model) if model is not None else None

    async def find_by_product(self, product_id: UUID) -> list[ProductSource]:
        """Busca las publicaciones asociadas a un producto normalizado."""
        models = await self._session.scalars(
            select(ProductSourceModel)
            .where(ProductSourceModel.producto_id == product_id)
            .order_by(ProductSourceModel.nombre_original)
        )
        return [product_source_model_to_entity(model) for model in models.all()]

    async def find_by_supermarket(self, supermarket_id: UUID) -> list[ProductSource]:
        """Busca las publicaciones pertenecientes a un supermercado."""
        models = await self._session.scalars(
            select(ProductSourceModel)
            .where(ProductSourceModel.supermercado_id == supermarket_id)
            .order_by(ProductSourceModel.nombre_original)
        )
        return [product_source_model_to_entity(model) for model in models.all()]

    async def find_by_external_code(
        self,
        supermarket_id: UUID,
        external_code: str,
    ) -> ProductSource | None:
        """Busca una publicación por supermercado y código externo."""
        model = await self._session.scalar(
            select(ProductSourceModel).where(
                ProductSourceModel.supermercado_id == supermarket_id,
                ProductSourceModel.codigo_externo == external_code,
            )
        )
        return product_source_model_to_entity(model) if model is not None else None

    async def save(self, product_source: ProductSource) -> ProductSource:
        """Crea o actualiza una publicación sin confirmar la transacción."""
        model = await self._session.get(ProductSourceModel, product_source.id)
        if model is None:
            model = product_source_entity_to_model(product_source)
            self._session.add(model)
        else:
            model.producto_id = product_source.product_id
            model.supermercado_id = product_source.supermarket_id
            model.nombre_original = product_source.original_name
            model.codigo_externo = product_source.external_code
            model.url_producto = product_source.product_url
            model.unidad_original = product_source.original_unit
            model.confianza_match = product_source.match_confidence
            model.activo = product_source.active

        await self._session.flush()
        return product_source_model_to_entity(model)

    async def save_many(self, product_sources: list[ProductSource]) -> list[ProductSource]:
        """Guarda múltiples publicaciones sin confirmar la transacción."""
        return [await self.save(product_source) for product_source in product_sources]
