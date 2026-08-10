"""Domain entity that preserves one extracted product through ETL processing."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


SCRAPED_PRODUCT_STATUSES = frozenset({"pending", "loaded", "rejected", "duplicate", "unmatched"})


@dataclass
class ScrapedProduct:
    """Stores a raw extraction and the result of its quality and loading checks."""

    id: UUID
    scraping_run_id: UUID
    raw_payload: dict[str, Any]
    external_code: str | None = None
    ean: str | None = None
    name: str | None = None
    brand: str | None = None
    amount: Decimal | None = None
    presentation: str | None = None
    product_url: str | None = None
    status: str = "pending"
    quality_message: str | None = None
    product_source_id: UUID | None = None
    price_id: UUID | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status not in SCRAPED_PRODUCT_STATUSES:
            raise ValueError(f"Invalid scraped product status: {self.status}.")
        if not isinstance(self.raw_payload, dict):
            raise ValueError("Scraped product raw payload must be an object.")
        self.external_code = self._clean(self.external_code)
        self.ean = self._clean(self.ean)
        self.name = self._clean(self.name)
        self.brand = self._clean(self.brand)
        self.presentation = self._clean(self.presentation)
        self.product_url = self._clean(self.product_url)
        self.quality_message = self._clean(self.quality_message)

    def mark_loaded(self, product_source_id: UUID, price_id: UUID, processed_at: datetime) -> None:
        self.status = "loaded"
        self.product_source_id = product_source_id
        self.price_id = price_id
        self.quality_message = None
        self.processed_at = processed_at

    def mark_rejected(self, message: str, processed_at: datetime) -> None:
        self._mark_without_load("rejected", message, processed_at)

    def mark_duplicate(self, message: str, processed_at: datetime) -> None:
        self._mark_without_load("duplicate", message, processed_at)

    def mark_unmatched(self, message: str, processed_at: datetime) -> None:
        self._mark_without_load("unmatched", message, processed_at)

    def _mark_without_load(self, status: str, message: str, processed_at: datetime) -> None:
        if not message or not message.strip():
            raise ValueError("Scraped product quality message cannot be empty.")
        self.status = status
        self.quality_message = message.strip()[:1000]
        self.product_source_id = None
        self.price_id = None
        self.processed_at = processed_at

    @staticmethod
    def _clean(value: str | None) -> str | None:
        return value.strip() or None if value is not None else None
