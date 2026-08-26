"""Reconciles historical source publications against curated canonical products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.catalog.domain.entities import Product
from app.modules.ingestion.infrastructure.etl import (
    ProductIdentityCandidate,
    ProductIdentityMatcher,
)
from app.shared.application import UnitOfWorkPort


@dataclass(frozen=True)
class ProductIdentitySuggestionDTO:
    product_source_id: UUID
    source_name: str
    current_product_id: UUID
    current_product_name: str
    target_product_id: UUID
    target_product_name: str
    confidence: Decimal
    method: str


@dataclass(frozen=True)
class ProductIdentityReconciliationDTO:
    dry_run: bool
    scanned_sources: int
    curated_products: int
    suggestions: list[ProductIdentitySuggestionDTO]
    reassigned_sources: int
    deactivated_products: int


class ReconcileProductIdentityUseCase:
    """Moves weak source-created products only when one curated candidate matches."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, *, apply: bool = False) -> ProductIdentityReconciliationDTO:
        async with self._unit_of_work as uow:
            products = await uow.products.list_active(limit=10_000)
            products_by_id = {product.id: product for product in products}
            brands = await uow.brands.list_active()
            brand_names = {brand.id: brand.name for brand in brands}
            curated = [product for product in products if _is_curated(product)]
            candidates = [
                ProductIdentityCandidate(
                    product=product,
                    brand_name=brand_names.get(product.brand_id),
                )
                for product in curated
            ]
            product_sources = await uow.product_sources.list_all()
            matcher = ProductIdentityMatcher()
            suggestions: list[ProductIdentitySuggestionDTO] = []

            for product_source in product_sources:
                current = products_by_id.get(product_source.product_id)
                if current is None or _is_curated(current):
                    continue
                match = matcher.match(
                    name=product_source.original_name,
                    presentation=product_source.original_unit,
                    brand=None,
                    candidates=candidates,
                )
                if match is None or match.product.id == current.id:
                    continue
                suggestions.append(
                    ProductIdentitySuggestionDTO(
                        product_source_id=product_source.id,
                        source_name=product_source.original_name,
                        current_product_id=current.id,
                        current_product_name=current.normalized_name,
                        target_product_id=match.product.id,
                        target_product_name=match.product.normalized_name,
                        confidence=match.confidence,
                        method=match.method,
                    )
                )

            deactivated = 0
            if apply:
                suggestions_by_source = {
                    suggestion.product_source_id: suggestion for suggestion in suggestions
                }
                for product_source in product_sources:
                    suggestion = suggestions_by_source.get(product_source.id)
                    if suggestion is None:
                        continue
                    product_source.product_id = suggestion.target_product_id
                    product_source.match_confidence = suggestion.confidence
                    await uow.product_sources.save(product_source)

                remaining_product_ids = {source.product_id for source in product_sources}
                for product in products:
                    if _is_curated(product) or product.id in remaining_product_ids:
                        continue
                    product.deactivate()
                    await uow.products.save(product)
                    deactivated += 1
                await uow.commit()

        return ProductIdentityReconciliationDTO(
            dry_run=not apply,
            scanned_sources=len(product_sources),
            curated_products=len(curated),
            suggestions=suggestions,
            reassigned_sources=len(suggestions) if apply else 0,
            deactivated_products=deactivated,
        )


def _is_curated(product: Product) -> bool:
    """Curated products carry an internal identity or explicit catalog metadata."""
    return bool(
        product.internal_code
        or product.category_id
        or product.brand_id
        or (product.unit_measure and product.net_content is not None)
    )
