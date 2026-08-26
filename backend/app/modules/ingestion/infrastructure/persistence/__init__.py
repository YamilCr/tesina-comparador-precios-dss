"""Adaptadores de persistencia de ingesta."""

from .sqlalchemy_models import (
    ProductIdentityReviewModel,
    ScheduledRefreshExecutionModel,
    ScrapedProductModel,
    ScrapingRunModel,
    ScrapingScheduleModel,
    ScrapingSourceModel,
)
from .sqlalchemy_ingestion_repository import SQLAlchemyIngestionRepository

__all__ = [
    "SQLAlchemyIngestionRepository",
    "ProductIdentityReviewModel",
    "ScheduledRefreshExecutionModel",
    "ScrapedProductModel",
    "ScrapingRunModel",
    "ScrapingScheduleModel",
    "ScrapingSourceModel",
]
