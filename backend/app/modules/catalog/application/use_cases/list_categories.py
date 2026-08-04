"""Caso de uso para listar categorías de productos."""

from app.modules.catalog.application.dto import ProductCategoryDTO
from app.shared.application import UnitOfWorkPort


class ListCategoriesUseCase:
    """Lista categorías del catálogo mediante UnitOfWorkPort."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, active_only: bool = True) -> list[ProductCategoryDTO]:
        """Lista categorías activas o todas las categorías según el parámetro."""
        async with self._uow as uow:
            categories = (
                await uow.product_categories.list_active()
                if active_only
                else await uow.product_categories.list_all()
            )
            return [ProductCategoryDTO.from_entity(category) for category in categories]
