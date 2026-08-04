"""Caso de uso de compatibilidad para listar categorías activas del catálogo."""

from app.modules.catalog.application.dto import ProductCategoryDTO
from app.modules.catalog.application.use_cases.list_categories import ListCategoriesUseCase
from app.shared.application import UnitOfWorkPort


class ListActiveCategoriesUseCase:
    """Lista categorías activas sin conocer detalles de persistencia."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._delegate = ListCategoriesUseCase(uow)

    async def execute(self) -> list[ProductCategoryDTO]:
        """Obtiene categorías activas del catálogo."""
        return await self._delegate.execute(active_only=True)
