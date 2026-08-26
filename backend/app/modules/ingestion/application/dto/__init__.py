"""Data transfer objects used by ingestion application use cases."""

from .ingestion_dto import (
    ConcurrentScrapingRefreshDTO,
    ConcurrentScrapingSourceResultDTO,
    ScheduledRefreshExecutionDTO,
    ScrapingBenchmarkDTO,
    ScrapingBenchmarkSourceDTO,
    EtlLoadResultDTO,
    ScrapingExecutionDTO,
    ScrapingRefreshDTO,
    ScrapingRunDTO,
    ScrapingScheduleDTO,
    ScrapingSourceDTO,
)

__all__ = [
    "ConcurrentScrapingRefreshDTO",
    "ConcurrentScrapingSourceResultDTO",
    "EtlLoadResultDTO",
    "ScheduledRefreshExecutionDTO",
    "ScrapingExecutionDTO",
    "ScrapingBenchmarkDTO",
    "ScrapingBenchmarkSourceDTO",
    "ScrapingRefreshDTO",
    "ScrapingRunDTO",
    "ScrapingScheduleDTO",
    "ScrapingSourceDTO",
]
