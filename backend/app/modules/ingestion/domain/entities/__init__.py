"""Entidades de dominio para fuentes y corridas de ingesta."""

from .scraping_run import ScrapingRun
from .scraping_source import ScrapingSource
from .scraped_product import ScrapedProduct

__all__ = ["ScrapedProduct", "ScrapingRun", "ScrapingSource"]
