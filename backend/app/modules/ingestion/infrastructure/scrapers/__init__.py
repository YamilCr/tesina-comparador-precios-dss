"""Adaptadores de scraping para fuentes externas de supermercados."""

from .coope_scraper import CoopeScraper, normalize_coope_product
from .jumbo_scraper import JumboScraper, normalize_jumbo_product

__all__ = [
    "CoopeScraper",
    "JumboScraper",
    "normalize_coope_product",
    "normalize_jumbo_product",
]
