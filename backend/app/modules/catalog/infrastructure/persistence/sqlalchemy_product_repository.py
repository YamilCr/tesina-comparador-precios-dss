"""Adaptador SQLAlchemy asíncrono para el puerto de productos normalizados."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.entities import Product
from app.modules.catalog.domain.ports import ProductRepositoryPort

from .mappers import product_entity_to_model, product_model_to_entity
from .sqlalchemy_models import ProductModel


class SQLAlchemyProductRepository(ProductRepositoryPort):
    """Implementa el acceso a productos mediante una sesión SQLAlchemy asíncrona."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, product_id: UUID) -> Product | None:
        """Obtiene un producto por identificador."""
        model = await self._session.get(ProductModel, product_id)
        return product_model_to_entity(model) if model is not None else None

    async def get_by_internal_code(self, internal_code: str) -> Product | None:
        """Obtiene un producto por su código interno."""
        model = await self._session.scalar(
            select(ProductModel).where(ProductModel.codigo_interno == internal_code)
        )
        return product_model_to_entity(model) if model is not None else None

    async def search_by_name(self, query: str, limit: int = 20) -> list[Product]:
        """Busca productos por nombre normalizado mediante coincidencia parcial."""
        models = await self._session.scalars(
            select(ProductModel)
            .where(ProductModel.nombre_normalizado.ilike(f"%{query}%"))
            .order_by(ProductModel.nombre_normalizado)
            .limit(limit)
        )
        return [product_model_to_entity(model) for model in models.all()]

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[Product]:
        """Lista productos activos con paginación básica."""
        models = await self._session.scalars(
            select(ProductModel)
            .where(ProductModel.activo.is_(True))
            .order_by(ProductModel.nombre_normalizado)
            .limit(limit)
            .offset(offset)
        )
        return [product_model_to_entity(model) for model in models.all()]

    async def save(self, product: Product) -> Product:
        """Crea o actualiza un producto sin confirmar la transacción."""
        model = await self._session.get(ProductModel, product.id)
        if model is None:
            model = product_entity_to_model(product)
            self._session.add(model)
        else:
            model.categoria_id = product.category_id
            model.marca_id = product.brand_id
            model.nombre_normalizado = product.normalized_name
            model.descripcion = product.description
            model.unidad_medida = product.unit_measure
            model.contenido_neto = product.net_content
            model.codigo_interno = product.internal_code
            model.activo = product.active

        await self._session.flush()
        return product_model_to_entity(model)
