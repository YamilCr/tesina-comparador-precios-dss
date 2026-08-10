"""Data transfer objects used by ingestion application use cases."""

from .ingestion_dto import (
    EtlLoadResultDTO,
    ScrapingExecutionDTO,
    ScrapingRefreshDTO,
    ScrapingRunDTO,
    ScrapingSourceDTO,
)

__all__ = [
    "EtlLoadResultDTO",
    "ScrapingExecutionDTO",
    "ScrapingRefreshDTO",
    "ScrapingRunDTO",
    "ScrapingSourceDTO",
]
