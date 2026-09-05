"""Caso de uso para buscar productos normalizados por nombre."""

import logging
from uuid import UUID

from app.modules.catalog.application.commands import SearchProductsQuery
from app.modules.catalog.application.dto import ProductDTO
from app.modules.catalog.domain.entities import Product
from app.modules.catalog.domain.ports import ProductSearchIndexPort
from app.shared.application import UnitOfWorkPort

logger = logging.getLogger(__name__)


class SearchProductsUseCase:
    """Busca productos del catálogo combinando texto determinístico y similitud opcional."""

    def __init__(
        self,
        uow: UnitOfWorkPort,
        search_index: ProductSearchIndexPort | None = None,
        *,
        vector_search_enabled: bool = False,
        vector_search_min_score: float = 0.35,
    ) -> None:
        """Recibe el Unit of Work que provee el repositorio de productos."""
        self._uow = uow
        self._search_index = search_index
        self._vector_search_enabled = vector_search_enabled
        self._vector_search_min_score = vector_search_min_score

    async def execute(
        self,
        query: SearchProductsQuery,
        *,
        category_id: UUID | None = None,
    ) -> list[ProductDTO]:
        """Busca productos y devuelve DTOs sin exponer scores semánticos."""
        async with self._uow as uow:
            textual_products = await uow.products.search_by_name(query.query, query.limit)
            textual_products = _filter_by_category(textual_products, category_id)

            if not self._vector_search_enabled or self._search_index is None:
                return [ProductDTO.from_entity(product) for product in textual_products]

            try:
                semantic_hits = await self._search_index.search(
                    query.query,
                    top_k=min(query.limit * 3, 50),
                )
            except Exception:
                logger.warning("Product semantic search failed; falling back to text", exc_info=True)
                return [ProductDTO.from_entity(product) for product in textual_products]

            semantic_ids = [
                hit.product_id
                for hit in semantic_hits
                if hit.score >= self._vector_search_min_score
            ]
            if not semantic_ids:
                return [ProductDTO.from_entity(product) for product in textual_products]
            semantic_products = await uow.products.list_active_by_ids(semantic_ids)
            semantic_products = _filter_by_category(semantic_products, category_id)
            products = _merge_products(textual_products, semantic_products, limit=query.limit)
            return [ProductDTO.from_entity(product) for product in products]


def _filter_by_category(
    products: list[Product],
    category_id: UUID | None,
) -> list[Product]:
    if category_id is None:
        return products
    return [product for product in products if product.category_id == category_id]


def _merge_products(
    textual_products: list[Product],
    semantic_products: list[Product],
    *,
    limit: int,
) -> list[Product]:
    merged: list[Product] = []
    seen_ids: set[UUID] = set()
    for product in [*textual_products, *semantic_products]:
        if product.id in seen_ids:
            continue
        merged.append(product)
        seen_ids.add(product.id)
        if len(merged) >= limit:
            break
    return merged
