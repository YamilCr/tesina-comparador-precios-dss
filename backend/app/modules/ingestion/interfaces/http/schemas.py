"""HTTP schemas for ingestion source configuration and run audit."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateScrapingSourceRequest(BaseModel):
    supermarket_id: UUID
    name: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=2048)
    scraper_key: Literal["carrefour", "coope", "jumbo", "la_anonima", "playwright"] = "jumbo"
    branch_id: UUID | None = None
    active: bool = True


class UpdateScrapingSourceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    scraper_key: Literal["carrefour", "coope", "jumbo", "la_anonima", "playwright"] | None = None
    branch_id: UUID | None = None
    active: bool | None = None


class CompleteScrapingRunRequest(BaseModel):
    items_scraped: int = Field(ge=0)
    items_loaded: int = Field(ge=0)


class FailScrapingRunRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=2000)


class RefreshScrapingSourceRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=5)
    city: str = Field(default="Comodoro Rivadavia", min_length=1, max_length=120)
    limit: int = Field(default=10, ge=1, le=20)


class ConcurrentRefreshScrapingSourcesRequest(RefreshScrapingSourceRequest):
    source_ids: list[UUID] = Field(min_length=1, max_length=10)
    max_concurrency: int = Field(default=3, ge=1, le=5)
    timeout_seconds: int = Field(default=20, ge=1, le=60)


class CreateScrapingScheduleRequest(BaseModel):
    source_id: UUID
    name: str = Field(min_length=1, max_length=255)
    queries: list[str] = Field(min_length=1, max_length=5)
    city: str = Field(default="Comodoro Rivadavia", min_length=1, max_length=120)
    interval_minutes: int = Field(default=1440, ge=1, le=10080)
    retry_delay_minutes: int = Field(default=5, ge=1, le=1440)
    result_limit: int = Field(default=10, ge=1, le=20)
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    next_run_at: datetime | None = None
    enabled: bool = True


class UpdateScrapingScheduleRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    queries: list[str] | None = Field(default=None, min_length=1, max_length=5)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    retry_delay_minutes: int | None = Field(default=None, ge=1, le=1440)
    result_limit: int | None = Field(default=None, ge=1, le=20)
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    next_run_at: datetime | None = None
    enabled: bool | None = None


class ScrapingSourceResponse(BaseModel):
    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
    scraper_key: str
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


class ScrapingScheduleResponse(BaseModel):
    id: UUID
    scraping_source_id: UUID
    name: str
    queries: list[str]
    city: str
    interval_minutes: int
    retry_delay_minutes: int
    result_limit: int
    timeout_seconds: int
    enabled: bool
    next_run_at: datetime
    locked_until: datetime | None
    consecutive_failures: int
    created_at: datetime | None
    updated_at: datetime | None


class ScheduledRefreshExecutionResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    scraping_run_id: UUID | None
    status: str
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime | None
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


class ConcurrentScrapingSourceResultResponse(BaseModel):
    source_id: UUID
    source_name: str
    run: ScrapingRunResponse
    duration_ms: int
    load: EtlLoadResultResponse | None = None
    error_message: str | None = None


class ConcurrentScrapingRefreshResponse(BaseModel):
    results: list[ConcurrentScrapingSourceResultResponse]
