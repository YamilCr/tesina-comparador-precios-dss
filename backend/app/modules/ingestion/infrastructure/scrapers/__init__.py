"""Adaptadores de scraping para fuentes externas de supermercados."""

from .carrefour_scraper import CarrefourScraper, normalize_carrefour_product
from .coope_scraper import CoopeScraper, normalize_coope_product
from .factory import create_scraper_for_source
from .jumbo_scraper import JumboScraper, normalize_jumbo_product
from .la_anonima_scraper import LaAnonimaScraper, normalize_la_anonima_product
from .playwright_worker_pool import PlaywrightWorkerPool
from .vtex_region import VtexLocationTarget, VtexRegionContext

__all__ = [
    "CoopeScraper",
    "CarrefourScraper",
    "create_scraper_for_source",
    "JumboScraper",
    "LaAnonimaScraper",
    "PlaywrightWorkerPool",
    "VtexLocationTarget",
    "VtexRegionContext",
    "normalize_coope_product",
    "normalize_carrefour_product",
    "normalize_jumbo_product",
    "normalize_la_anonima_product",
]
