"""Loads validated staged extraction records into the catalog and price history."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.catalog.domain.entities import Product, ProductSource
from app.modules.ingestion.application.dto import EtlLoadResultDTO
from app.modules.ingestion.infrastructure.etl import (
    clean_price,
    normalize_product,
    product_matching_key,
    validate_scraped_product,
)
from app.modules.prices.domain.entities import Price
from app.shared.application import UnitOfWorkPort


class LoadScrapingRunUseCase:
    """Applies quality checks, matching and idempotent price-history loading."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        run_id: UUID,
        branch_id: UUID | None = None,
        *,
        create_missing_products: bool = True,
    ) -> EtlLoadResultDTO:
        processed_at = datetime.now(timezone.utc)
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
            product_key_index = await self._build_product_key_index(uow)
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

                product_source = await uow.product_sources.find_by_external_code(
                    source.supermarket_id,
                    staged.external_code or "",
                )
                if product_source is None:
                    product = product_key_index.get(normalized.matching_key)
                    if product is None:
                        if not create_missing_products:
                            staged.mark_unmatched("No exact normalized product match.", processed_at)
                            result.unmatched += 1
                            continue
                        product = Product(id=uuid4(), normalized_name=normalized.name)
                        product = await uow.products.save(product)
                        product_key_index[normalized.matching_key] = product
                        result.created_products += 1
                        confidence = Decimal("1.000")
                    else:
                        confidence = Decimal("0.950")
                    product_source = ProductSource(
                        id=uuid4(),
                        product_id=product.id,
                        supermarket_id=source.supermarket_id,
                        original_name=normalized.name,
                        external_code=staged.external_code,
                        product_url=staged.product_url,
                        original_unit=normalized.original_unit,
                        match_confidence=confidence,
                    )
                else:
                    product_source.original_name = normalized.name
                    product_source.product_url = staged.product_url
                    product_source.original_unit = normalized.original_unit
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
        return result.to_dto()

    @staticmethod
    async def _build_product_key_index(uow: UnitOfWorkPort) -> dict[str, Product]:
        products = await uow.products.list_active(limit=1000)
        return {
            key: product
            for product in products
            if (key := product_matching_key(product.normalized_name))
        }


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
