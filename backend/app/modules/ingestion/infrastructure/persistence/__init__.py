"""Adaptadores de persistencia de ingesta."""

from .sqlalchemy_models import ScrapingRunModel, ScrapingSourceModel

__all__ = ["ScrapingRunModel", "ScrapingSourceModel"]
