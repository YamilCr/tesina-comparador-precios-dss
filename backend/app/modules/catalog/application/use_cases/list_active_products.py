"""Caso de uso para listar productos activos del catálogo."""

from app.modules.catalog.application.commands import ProductListQuery
from app.modules.catalog.application.dto import ProductDTO
from app.shared.application import UnitOfWorkPort


class ListActiveProductsUseCase:
    """Lista productos activos sin conocer detalles de infraestructura."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work que provee los puertos de repositorio."""
        self._uow = uow

    async def execute(self, query: ProductListQuery | None = None) -> list[ProductDTO]:
        """Obtiene productos activos aplicando paginación básica."""
        query = query or ProductListQuery()
        async with self._uow as uow:
            products = await uow.products.list_active(limit=query.limit, offset=query.offset)
            return [ProductDTO.from_entity(product) for product in products]
