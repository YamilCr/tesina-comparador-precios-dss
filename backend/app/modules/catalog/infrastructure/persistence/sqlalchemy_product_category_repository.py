"""Adaptador SQLAlchemy asíncrono para el puerto de categorías de producto."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.entities import ProductCategory
from app.modules.catalog.domain.ports import ProductCategoryRepositoryPort

from .mappers import product_category_entity_to_model, product_category_model_to_entity
from .sqlalchemy_models import ProductCategoryModel


class SQLAlchemyProductCategoryRepository(ProductCategoryRepositoryPort):
    """Implementa el acceso a categorías mediante una sesión SQLAlchemy asíncrona."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, category_id: UUID) -> ProductCategory | None:
        """Obtiene una categoría por identificador."""
        model = await self._session.get(ProductCategoryModel, category_id)
        return product_category_model_to_entity(model) if model is not None else None

    async def get_by_name(self, name: str) -> ProductCategory | None:
        """Obtiene una categoría por nombre."""
        model = await self._session.scalar(
            select(ProductCategoryModel).where(ProductCategoryModel.nombre == name)
        )
        return product_category_model_to_entity(model) if model is not None else None

    async def list_active(self) -> list[ProductCategory]:
        """Lista las categorías activas ordenadas por nombre."""
        models = await self._session.scalars(
            select(ProductCategoryModel)
            .where(ProductCategoryModel.activo.is_(True))
            .order_by(ProductCategoryModel.nombre)
        )
        return [product_category_model_to_entity(model) for model in models.all()]

    async def list_all(self) -> list[ProductCategory]:
        """Lista todas las categorías ordenadas por nombre."""
        models = await self._session.scalars(
            select(ProductCategoryModel).order_by(ProductCategoryModel.nombre)
        )
        return [product_category_model_to_entity(model) for model in models.all()]

    async def save(self, category: ProductCategory) -> ProductCategory:
        """Crea o actualiza una categoría sin confirmar la transacción."""
        model = await self._session.get(ProductCategoryModel, category.id)
        if model is None:
            model = product_category_entity_to_model(category)
            self._session.add(model)
        else:
            model.nombre = category.name
            model.descripcion = category.description
            model.categoria_padre_id = category.parent_category_id
            model.activo = category.active

        await self._session.flush()
        return product_category_model_to_entity(model)
