"""Adaptadores de persistencia de ingesta."""

from .sqlalchemy_models import ScrapedProductModel, ScrapingRunModel, ScrapingSourceModel
from .sqlalchemy_ingestion_repository import SQLAlchemyIngestionRepository

__all__ = [
    "SQLAlchemyIngestionRepository",
    "ScrapedProductModel",
    "ScrapingRunModel",
    "ScrapingSourceModel",
]
