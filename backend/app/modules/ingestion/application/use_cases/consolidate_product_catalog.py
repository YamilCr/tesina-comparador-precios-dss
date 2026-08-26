"""Consolidates exact multi-supermarket product duplicates into canonical records."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.catalog.domain.entities import Brand, Product, ProductSource
from app.modules.ingestion.infrastructure.etl import (
    build_product_identity,
    catalog_quantity_fields,
    normalized_token_set,
    product_matching_key,
)
from app.shared.application import UnitOfWorkPort


@dataclass(frozen=True)
class CanonicalProductClusterDTO:
    matching_key: str
    target_product_id: UUID
    target_product_name: str
    duplicate_product_ids: tuple[UUID, ...]
    duplicate_product_names: tuple[str, ...]
    source_count: int
    supermarket_count: int


@dataclass(frozen=True)
class ProductCatalogConsolidationDTO:
    dry_run: bool
    scanned_products: int
    clusters: list[CanonicalProductClusterDTO]
    reassigned_sources: int
    deactivated_products: int
    enriched_products: int


class ConsolidateProductCatalogUseCase:
    """Merges only exact identity keys independently observed by multiple chains."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, *, apply: bool = False) -> ProductCatalogConsolidationDTO:
        async with self._unit_of_work as uow:
            products = await uow.products.list_active(limit=10_000)
            product_sources = [
                source for source in await uow.product_sources.list_all() if source.active
            ]
            brands = await uow.brands.list_active()
            sources_by_product = _sources_by_product(product_sources)
            grouped_products = _products_by_matching_key(products)
            clusters: list[CanonicalProductClusterDTO] = []
            cluster_targets: dict[str, Product] = {}
            source_reassignments: dict[UUID, UUID] = {}
            duplicate_ids: set[UUID] = set()

            for matching_key, group in sorted(grouped_products.items()):
                if len(group) < 2:
                    continue
                group_sources = [
                    source
                    for product in group
                    for source in sources_by_product.get(product.id, [])
                ]
                supermarket_ids = {source.supermarket_id for source in group_sources}
                if len(supermarket_ids) < 2:
                    continue
                identity = build_product_identity(group[0].normalized_name)
                if identity.quantity is None:
                    continue

                target = _select_target(group, sources_by_product)
                duplicates = sorted(
                    (product for product in group if product.id != target.id),
                    key=lambda product: (product.normalized_name.casefold(), str(product.id)),
                )
                clusters.append(
                    CanonicalProductClusterDTO(
                        matching_key=matching_key,
                        target_product_id=target.id,
                        target_product_name=target.normalized_name,
                        duplicate_product_ids=tuple(product.id for product in duplicates),
                        duplicate_product_names=tuple(
                            product.normalized_name for product in duplicates
                        ),
                        source_count=len(group_sources),
                        supermarket_count=len(supermarket_ids),
                    )
                )
                cluster_targets[matching_key] = target
                duplicate_ids.update(product.id for product in duplicates)
                for source in group_sources:
                    if source.product_id != target.id:
                        source_reassignments[source.id] = target.id

            enriched = 0
            if apply:
                sources_by_id = {source.id: source for source in product_sources}
                products_by_id = {product.id: product for product in products}
                for source_id, target_id in source_reassignments.items():
                    source = sources_by_id[source_id]
                    source.product_id = target_id
                    source.match_confidence = Decimal("0.950")
                    await uow.product_sources.save(source)

                for matching_key, target in cluster_targets.items():
                    if _enrich_target(target, brands):
                        await uow.products.save(target)
                        enriched += 1

                for duplicate_id in duplicate_ids:
                    duplicate = products_by_id[duplicate_id]
                    duplicate.deactivate()
                    await uow.products.save(duplicate)
                await uow.commit()

        return ProductCatalogConsolidationDTO(
            dry_run=not apply,
            scanned_products=len(products),
            clusters=clusters,
            reassigned_sources=len(source_reassignments) if apply else 0,
            deactivated_products=len(duplicate_ids) if apply else 0,
            enriched_products=enriched,
        )


def _products_by_matching_key(products: list[Product]) -> dict[str, list[Product]]:
    groups: dict[str, list[Product]] = defaultdict(list)
    for product in products:
        matching_key = product_matching_key(product.normalized_name)
        if matching_key:
            groups[matching_key].append(product)
    return groups


def _sources_by_product(
    product_sources: list[ProductSource],
) -> dict[UUID, list[ProductSource]]:
    groups: dict[UUID, list[ProductSource]] = defaultdict(list)
    for source in product_sources:
        groups[source.product_id].append(source)
    return groups


def _select_target(
    products: list[Product],
    sources_by_product: dict[UUID, list[ProductSource]],
) -> Product:
    return min(
        products,
        key=lambda product: (
            not _has_catalog_metadata(product),
            -len(sources_by_product.get(product.id, [])),
            len(product.normalized_name),
            product.normalized_name.casefold(),
            str(product.id),
        ),
    )


def _has_catalog_metadata(product: Product) -> bool:
    return bool(
        product.internal_code
        or product.category_id
        or product.brand_id
        or (product.unit_measure and product.net_content is not None)
    )


def _enrich_target(target: Product, brands: list[Brand]) -> bool:
    changed = False
    identity = build_product_identity(target.normalized_name)
    unit_measure, net_content = catalog_quantity_fields(identity.quantity)
    if target.unit_measure is None and unit_measure is not None:
        target.unit_measure = unit_measure
        changed = True
    if target.net_content is None and net_content is not None:
        target.net_content = net_content
        changed = True
    if target.brand_id is None:
        identity_tokens = identity.tokens
        matching_brands = [
            brand
            for brand in brands
            if normalized_token_set(brand.name)
            and normalized_token_set(brand.name) <= identity_tokens
        ]
        if len(matching_brands) == 1:
            target.brand_id = matching_brands[0].id
            changed = True
    return changed
