"""Caso de uso para buscar productos normalizados por nombre."""

from app.modules.catalog.application.commands import SearchProductsQuery
from app.modules.catalog.application.dto import ProductDTO
from app.shared.application import UnitOfWorkPort


class SearchProductsUseCase:
    """Busca productos del catálogo usando únicamente puertos del dominio."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work que provee el repositorio de productos."""
        self._uow = uow

    async def execute(self, query: SearchProductsQuery) -> list[ProductDTO]:
        """Busca productos por nombre normalizado y devuelve DTOs."""
        async with self._uow as uow:
            products = await uow.products.search_by_name(query.query, query.limit)
            return [ProductDTO.from_entity(product) for product in products]
