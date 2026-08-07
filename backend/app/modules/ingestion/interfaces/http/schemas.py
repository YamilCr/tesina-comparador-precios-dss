"""HTTP schemas for ingestion source configuration and run audit."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateScrapingSourceRequest(BaseModel):
    supermarket_id: UUID
    name: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=2048)
    active: bool = True


class UpdateScrapingSourceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    active: bool | None = None


class CompleteScrapingRunRequest(BaseModel):
    items_scraped: int = Field(ge=0)
    items_loaded: int = Field(ge=0)


class FailScrapingRunRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=2000)


class ScrapingSourceResponse(BaseModel):
    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
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
