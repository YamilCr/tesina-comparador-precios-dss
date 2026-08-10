"""HTTP schemas for ingestion source configuration and run audit."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateScrapingSourceRequest(BaseModel):
    supermarket_id: UUID
    name: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=2048)
    branch_id: UUID | None = None
    active: bool = True


class UpdateScrapingSourceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    branch_id: UUID | None = None
    active: bool | None = None


class CompleteScrapingRunRequest(BaseModel):
    items_scraped: int = Field(ge=0)
    items_loaded: int = Field(ge=0)


class FailScrapingRunRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=2000)


class RefreshScrapingSourceRequest(BaseModel):
    scraper: Literal["jumbo", "coope"]
    queries: list[str] = Field(min_length=1, max_length=5)
    city: str = Field(default="Comodoro Rivadavia", min_length=1, max_length=120)
    limit: int = Field(default=10, ge=1, le=20)


class ScrapingSourceResponse(BaseModel):
    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
    branch_id: UUID | None
    active: bool
    created_at: datetime | None


class ScrapingRunResponse(BaseModel):
    id: UUID
    scraping_source_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    items_scraped: int
    items_loaded: int
    error_message: str | None


class EtlLoadResultResponse(BaseModel):
    run_id: UUID
    processed: int
    loaded: int
    rejected: int
    duplicates: int
    unmatched: int
    created_products: int
    created_prices: int


class ScrapingRefreshResponse(BaseModel):
    run: ScrapingRunResponse
    load: EtlLoadResultResponse
