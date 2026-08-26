"""Enriches catalog identity from consistent loaded staging evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.catalog.domain.entities import Brand
from app.modules.ingestion.infrastructure.etl import normalize_gtin, normalized_brand_key
from app.shared.application import UnitOfWorkPort


GENERIC_BRAND_KEYS = frozenset({"generico", "sinmarca"})


@dataclass(frozen=True)
class BrandEnrichmentSuggestionDTO:
    product_id: UUID
    product_name: str
    brand_name: str
    creates_brand: bool
    evidence_rows: int
    evidence_sources: int


@dataclass(frozen=True)
class GtinBackfillSuggestionDTO:
    product_source_id: UUID
    product_id: UUID
    source_name: str
    gtin: str
    evidence_rows: int


@dataclass(frozen=True)
class GtinConflictDTO:
    gtin: str
    product_ids: tuple[UUID, ...]
    product_source_ids: tuple[UUID, ...]
    reason: str


@dataclass(frozen=True)
class ProductCatalogEnrichmentDTO:
    dry_run: bool
    evidence_rows: int
    brand_suggestions: list[BrandEnrichmentSuggestionDTO]
    gtin_suggestions: list[GtinBackfillSuggestionDTO]
    gtin_conflicts: list[GtinConflictDTO]
    created_brands: int
    enriched_products: int
    enriched_product_sources: int


class EnrichProductCatalogUseCase:
    """Applies only consensus brands and conflict-free declared GTIN evidence."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, *, apply: bool = False) -> ProductCatalogEnrichmentDTO:
        async with self._unit_of_work as uow:
            products = await uow.products.list_active(limit=10_000)
            product_sources = [
                source for source in await uow.product_sources.list_all() if source.active
            ]
            brands = await uow.brands.list_active()
            evidence = await uow.ingestion.list_loaded_scraped_products()
            products_by_id = {product.id: product for product in products}
            sources_by_id = {source.id: source for source in product_sources}
            existing_brands = {
                normalized_brand_key(brand.name): brand
                for brand in brands
                if normalized_brand_key(brand.name)
            }

            brand_suggestions, brand_keys = _brand_suggestions(
                evidence=evidence,
                products_by_id=products_by_id,
                sources_by_id=sources_by_id,
                existing_brands=existing_brands,
            )
            gtin_suggestions, gtin_conflicts = _gtin_suggestions(
                evidence=evidence,
                sources_by_id=sources_by_id,
            )

            created_brands = 0
            enriched_products = 0
            enriched_sources = 0
            if apply:
                brands_by_key = dict(existing_brands)
                for suggestion in brand_suggestions:
                    brand_key = brand_keys[suggestion.product_id]
                    brand = brands_by_key.get(brand_key)
                    if brand is None:
                        brand = await uow.brands.save(
                            Brand(id=uuid4(), name=suggestion.brand_name)
                        )
                        brands_by_key[brand_key] = brand
                        created_brands += 1
                    product = products_by_id[suggestion.product_id]
                    product.brand_id = brand.id
                    await uow.products.save(product)
                    enriched_products += 1

                for suggestion in gtin_suggestions:
                    product_source = sources_by_id[suggestion.product_source_id]
                    product_source.gtin = suggestion.gtin
                    await uow.product_sources.save(product_source)
                    enriched_sources += 1
                await uow.commit()

        return ProductCatalogEnrichmentDTO(
            dry_run=not apply,
            evidence_rows=len(evidence),
            brand_suggestions=brand_suggestions,
            gtin_suggestions=gtin_suggestions,
            gtin_conflicts=gtin_conflicts,
            created_brands=created_brands,
            enriched_products=enriched_products,
            enriched_product_sources=enriched_sources,
        )


def _brand_suggestions(*, evidence, products_by_id, sources_by_id, existing_brands):
    names_by_product: dict[UUID, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    global_names_by_key: dict[str, Counter[str]] = defaultdict(Counter)
    sources_by_product_brand: dict[tuple[UUID, str], set[UUID]] = defaultdict(set)
    for staged in evidence:
        source = sources_by_id.get(staged.product_source_id)
        if source is None or source.product_id not in products_by_id:
            continue
        product = products_by_id[source.product_id]
        if product.brand_id is not None:
            continue
        brand_key = normalized_brand_key(staged.brand)
        if not brand_key or brand_key in GENERIC_BRAND_KEYS or staged.brand is None:
            continue
        names_by_product[product.id][brand_key][staged.brand.strip()] += 1
        global_names_by_key[brand_key][staged.brand.strip()] += 1
        sources_by_product_brand[(product.id, brand_key)].add(source.id)

    suggestions: list[BrandEnrichmentSuggestionDTO] = []
    brand_keys: dict[UUID, str] = {}
    for product_id, names_by_key in names_by_product.items():
        if len(names_by_key) != 1:
            continue
        brand_key, names = next(iter(names_by_key.items()))
        existing = existing_brands.get(brand_key)
        brand_name = (
            existing.name
            if existing is not None
            else _preferred_brand_name(global_names_by_key[brand_key])
        )
        suggestions.append(
            BrandEnrichmentSuggestionDTO(
                product_id=product_id,
                product_name=products_by_id[product_id].normalized_name,
                brand_name=brand_name,
                creates_brand=existing is None,
                evidence_rows=sum(names.values()),
                evidence_sources=len(sources_by_product_brand[(product_id, brand_key)]),
            )
        )
        brand_keys[product_id] = brand_key
    suggestions.sort(key=lambda item: (item.brand_name.casefold(), item.product_name.casefold()))
    return suggestions, brand_keys


def _preferred_brand_name(names: Counter[str]) -> str:
    return min(
        names,
        key=lambda name: (
            name.isupper(),
            -names[name],
            len(name),
            name.casefold(),
        ),
    )


def _gtin_suggestions(*, evidence, sources_by_id):
    gtins_by_source: dict[UUID, Counter[str]] = defaultdict(Counter)
    for staged in evidence:
        if staged.product_source_id not in sources_by_id:
            continue
        identifier_type = staged.raw_payload.get("identifier_type")
        if not isinstance(identifier_type, str):
            continue
        gtin = normalize_gtin(staged.ean, identifier_type=identifier_type)
        if gtin is not None:
            gtins_by_source[staged.product_source_id][gtin] += 1

    candidate_gtins = {
        source_id: next(iter(gtins))
        for source_id, gtins in gtins_by_source.items()
        if len(gtins) == 1
    }
    source_ids_by_gtin: dict[str, set[UUID]] = defaultdict(set)
    product_ids_by_gtin: dict[str, set[UUID]] = defaultdict(set)
    for source_id, gtin in candidate_gtins.items():
        source_ids_by_gtin[gtin].add(source_id)
        product_ids_by_gtin[gtin].add(sources_by_id[source_id].product_id)

    conflicts: list[GtinConflictDTO] = []
    conflicting_gtins = {
        gtin for gtin, product_ids in product_ids_by_gtin.items() if len(product_ids) > 1
    }
    for gtin in sorted(conflicting_gtins):
        conflicts.append(
            GtinConflictDTO(
                gtin=gtin,
                product_ids=tuple(sorted(product_ids_by_gtin[gtin], key=str)),
                product_source_ids=tuple(sorted(source_ids_by_gtin[gtin], key=str)),
                reason="GTIN is linked to multiple active products.",
            )
        )

    suggestions: list[GtinBackfillSuggestionDTO] = []
    for source_id, gtin in candidate_gtins.items():
        source = sources_by_id[source_id]
        if gtin in conflicting_gtins or source.gtin == gtin:
            continue
        if source.gtin is not None and source.gtin != gtin:
            conflicts.append(
                GtinConflictDTO(
                    gtin=gtin,
                    product_ids=(source.product_id,),
                    product_source_ids=(source.id,),
                    reason=f"Publication already stores a different GTIN: {source.gtin}.",
                )
            )
            continue
        suggestions.append(
            GtinBackfillSuggestionDTO(
                product_source_id=source.id,
                product_id=source.product_id,
                source_name=source.original_name,
                gtin=gtin,
                evidence_rows=gtins_by_source[source_id][gtin],
            )
        )
    suggestions.sort(key=lambda item: (item.gtin, item.source_name.casefold()))
    conflicts.sort(key=lambda item: (item.gtin, item.reason))
    return suggestions, conflicts
