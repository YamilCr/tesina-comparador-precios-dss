"""Loads validated staged extraction records into the catalog and price history."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.catalog.domain.entities import Product, ProductSource
from app.modules.catalog.application.services import build_product_search_entry
from app.modules.catalog.domain.ports import ProductSearchIndexEntry, ProductSearchIndexPort
from app.modules.ingestion.application.dto import EtlLoadResultDTO
from app.modules.ingestion.domain.entities import ScrapedProduct
from app.modules.ingestion.infrastructure.etl import (
    ProductIdentityCandidate,
    ProductIdentityMatcher,
    catalog_quantity_fields,
    clean_price,
    normalize_gtin,
    normalize_product,
    normalized_token_set,
    validate_scraped_product,
)
from app.modules.prices.domain.entities import Price
from app.shared.application import UnitOfWorkPort

logger = logging.getLogger(__name__)


class LoadScrapingRunUseCase:
    """Applies quality checks, canonical identity matching and idempotent history loading."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        product_search_index: ProductSearchIndexPort | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._product_search_index = product_search_index

    async def execute(
        self,
        run_id: UUID,
        branch_id: UUID | None = None,
        *,
        create_missing_products: bool = True,
    ) -> EtlLoadResultDTO:
        processed_at = datetime.now(timezone.utc)
        created_search_entries: list[ProductSearchIndexEntry] = []
        async with self._unit_of_work as uow:
            run = await uow.ingestion.get_run_by_id(run_id)
            if run is None:
                raise ValueError("Scraping run not found.")
            if run.status != "succeeded":
                raise ValueError("Only succeeded scraping runs can be loaded.")
            source = await uow.ingestion.get_source_by_id(run.scraping_source_id)
            if source is None:
                raise ValueError("Scraping source not found.")
            branch_id = branch_id or source.branch_id
            if branch_id is None:
                raise ValueError("No target branch is configured for the scraping source.")
            branch = await uow.branches.get_by_id(branch_id)
            if branch is None or not branch.active:
                raise ValueError("Branch not found or inactive.")
            if branch.supermarket_id != source.supermarket_id:
                raise ValueError("Branch must belong to the scraping source supermarket.")

            all_staged = await uow.ingestion.list_scraped_products(run_id)
            loaded_before = sum(product.status == "loaded" for product in all_staged)
            staged_products = [
                product for product in all_staged if product.status in {"pending", "unmatched"}
            ]
            catalog = await self._build_catalog_identity_state(uow)
            matcher = ProductIdentityMatcher()
            seen_external_codes: set[str] = set()
            result = _MutableEtlResult(run_id=run_id)

            for staged in staged_products:
                result.processed += 1
                external_key = (staged.external_code or "").casefold()
                if external_key and external_key in seen_external_codes:
                    staged.mark_duplicate(
                        "Duplicate external code in the same scraping run.",
                        processed_at,
                    )
                    result.duplicates += 1
                    continue
                if external_key:
                    seen_external_codes.add(external_key)

                issues = validate_scraped_product(staged)
                try:
                    amount = clean_price(staged.amount)
                    normalized = normalize_product(staged.name or "", staged.presentation)
                    if not normalized.matching_key:
                        raise ValueError("Product name has no meaningful matching tokens.")
                except ValueError as error:
                    issues.append(str(error))
                    amount = None
                    normalized = None
                if issues:
                    staged.mark_rejected(" ".join(issues), processed_at)
                    result.rejected += 1
                    continue
                assert normalized is not None and amount is not None

                product_source = await uow.product_sources.find_by_external_code(
                    source.supermarket_id,
                    staged.external_code or "",
                )
                if product_source is None:
                    gtin = _staged_gtin(staged)
                    product, confidence, identity_error = await self._resolve_product(
                        uow=uow,
                        catalog=catalog,
                        matcher=matcher,
                        normalized=normalized,
                        brand=staged.brand,
                        gtin=gtin,
                    )
                    if identity_error is not None:
                        staged.mark_unmatched(identity_error, processed_at)
                        result.unmatched += 1
                        continue
                    if product is None:
                        if not create_missing_products:
                            staged.mark_unmatched(
                                "No unambiguous canonical product match.",
                                processed_at,
                            )
                            result.unmatched += 1
                            continue
                        unit_measure, net_content = catalog_quantity_fields(
                            normalized.identity.quantity
                        )
                        brand_id, brand_name = catalog.find_brand(staged.brand)
                        product = await uow.products.save(
                            Product(
                                id=uuid4(),
                                normalized_name=normalized.name,
                                brand_id=brand_id,
                                unit_measure=unit_measure,
                                net_content=net_content,
                            )
                        )
                        catalog.add_product(product, brand_name=brand_name)
                        created_search_entries.append(
                            build_product_search_entry(product, brand_name=brand_name)
                        )
                        result.created_products += 1
                        confidence = Decimal("1.000")
                    product_source = ProductSource(
                        id=uuid4(),
                        product_id=product.id,
                        supermarket_id=source.supermarket_id,
                        original_name=normalized.name,
                        external_code=staged.external_code,
                        product_url=staged.product_url,
                        original_unit=normalized.original_unit,
                        match_confidence=confidence,
                        gtin=gtin,
                    )
                else:
                    product_source.original_name = normalized.name
                    product_source.product_url = staged.product_url
                    product_source.original_unit = normalized.original_unit
                    product_source.gtin = product_source.gtin or _staged_gtin(staged)
                    product_source.activate()
                product_source = await uow.product_sources.save(product_source)

                observed_at = run.finished_at or run.started_at
                price = await uow.prices.find_by_product_source_branch_and_observed_at(
                    product_source.id,
                    branch.id,
                    observed_at,
                )
                if price is None:
                    price = await uow.prices.save(
                        Price(
                            id=uuid4(),
                            product_source_id=product_source.id,
                            branch_id=branch.id,
                            amount=amount,
                            observed_at=observed_at,
                        )
                    )
                    result.created_prices += 1
                staged.mark_loaded(product_source.id, price.id, processed_at)
                result.loaded += 1

            await uow.ingestion.save_scraped_products(staged_products)
            run.record_loaded_items(loaded_before + result.loaded)
            await uow.ingestion.save_run(run)
            await uow.commit()
        await self._upsert_created_product_vectors(created_search_entries)
        return result.to_dto()

    async def _upsert_created_product_vectors(
        self,
        entries: list[ProductSearchIndexEntry],
    ) -> None:
        if self._product_search_index is None or not entries:
            return
        try:
            await self._product_search_index.upsert_products(entries)
        except Exception:
            logger.warning(
                "Product search vector upsert failed after ETL load; rebuild can repair it.",
                exc_info=True,
            )

    @staticmethod
    async def _resolve_product(
        *,
        uow: UnitOfWorkPort,
        catalog: "_CatalogIdentityState",
        matcher: ProductIdentityMatcher,
        normalized,
        brand: str | None,
        gtin: str | None,
    ) -> tuple[Product | None, Decimal | None, str | None]:
        if gtin is not None:
            gtin_sources = await uow.product_sources.find_by_gtin(gtin)
            product_ids = {source.product_id for source in gtin_sources}
            if len(product_ids) > 1:
                return None, None, "GTIN is associated with multiple canonical products."
            if product_ids:
                product_id = next(iter(product_ids))
                product = catalog.products_by_id.get(product_id)
                if product is None:
                    product = await uow.products.get_by_id(product_id)
                if product is not None:
                    return product, Decimal("1.000"), None

        match = matcher.match(
            name=normalized.name,
            presentation=normalized.original_unit,
            brand=brand,
            candidates=catalog.candidates,
        )
        if match is None:
            return None, None, None
        return match.product, match.confidence, None

    @staticmethod
    async def _build_catalog_identity_state(uow: UnitOfWorkPort) -> "_CatalogIdentityState":
        products = await uow.products.list_active(limit=1000)
        brands = await uow.brands.list_active()
        brand_names = {brand.id: brand.name for brand in brands}
        return _CatalogIdentityState(
            candidates=[
                ProductIdentityCandidate(
                    product=product,
                    brand_name=brand_names.get(product.brand_id),
                )
                for product in products
            ],
            products_by_id={product.id: product for product in products},
            brands_by_tokens={
                normalized_token_set(brand.name): (brand.id, brand.name) for brand in brands
            },
        )


@dataclass
class _CatalogIdentityState:
    candidates: list[ProductIdentityCandidate]
    products_by_id: dict[UUID, Product]
    brands_by_tokens: dict[frozenset[str], tuple[UUID, str]]

    def find_brand(self, brand: str | None) -> tuple[UUID | None, str | None]:
        match = self.brands_by_tokens.get(normalized_token_set(brand))
        return match if match is not None else (None, None)

    def add_product(self, product: Product, *, brand_name: str | None) -> None:
        self.products_by_id[product.id] = product
        self.candidates.append(ProductIdentityCandidate(product=product, brand_name=brand_name))


def _staged_gtin(staged: ScrapedProduct) -> str | None:
    identifier_type = staged.raw_payload.get("identifier_type")
    if not isinstance(identifier_type, str):
        return None
    return normalize_gtin(staged.ean, identifier_type=identifier_type)


class _MutableEtlResult:
    """Internal counter object kept mutable while one transaction is processed."""

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        self.processed = 0
        self.loaded = 0
        self.rejected = 0
        self.duplicates = 0
        self.unmatched = 0
        self.created_products = 0
        self.created_prices = 0

    def to_dto(self) -> EtlLoadResultDTO:
        return EtlLoadResultDTO(
            run_id=self.run_id,
            processed=self.processed,
            loaded=self.loaded,
            rejected=self.rejected,
            duplicates=self.duplicates,
            unmatched=self.unmatched,
            created_products=self.created_products,
            created_prices=self.created_prices,
        )
