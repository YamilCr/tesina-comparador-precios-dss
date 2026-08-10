"""Stores raw scraper output before ETL quality processing."""

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from app.modules.ingestion.domain.entities import ScrapedProduct
from app.shared.application import UnitOfWorkPort


class StoreScrapedProductsUseCase:
    """Persists one immutable staging record for every item returned by a scraper."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, run_id: UUID, items: list[dict[str, Any]]) -> list[ScrapedProduct]:
        staged_products = [self._from_payload(run_id, item) for item in items]
        async with self._unit_of_work as uow:
            if await uow.ingestion.get_run_by_id(run_id) is None:
                raise ValueError("Scraping run not found.")
            saved_products = await uow.ingestion.save_scraped_products(staged_products)
            await uow.commit()
        return saved_products

    @staticmethod
    def _from_payload(run_id: UUID, payload: dict[str, Any]) -> ScrapedProduct:
        raw_payload = dict(payload)
        return ScrapedProduct(
            id=uuid4(),
            scraping_run_id=run_id,
            raw_payload=raw_payload,
            external_code=_as_text(payload.get("external_id")),
            ean=_as_text(payload.get("ean")),
            name=_as_text(payload.get("name")),
            brand=_as_text(payload.get("brand")),
            amount=_as_decimal(payload.get("price")),
            presentation=_as_text(payload.get("presentation")),
            product_url=_as_text(payload.get("url")),
        )


def _as_text(value: object) -> str | None:
    return str(value).strip() or None if value is not None else None


def _as_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
