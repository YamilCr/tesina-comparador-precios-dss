"""Adaptadores de persistencia de ingesta."""

from .sqlalchemy_models import ScrapingRunModel, ScrapingSourceModel
from .sqlalchemy_ingestion_repository import SQLAlchemyIngestionRepository

__all__ = [
    "SQLAlchemyIngestionRepository",
    "ScrapingRunModel",
    "ScrapingSourceModel",
]
