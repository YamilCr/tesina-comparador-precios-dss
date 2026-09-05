"""Adaptadores de scraping para fuentes externas de supermercados."""

from .carrefour_scraper import CarrefourScraper, normalize_carrefour_product
from .changomas_scraper import ChangoMasScraper, normalize_changomas_product
from .coope_scraper import CoopeScraper, normalize_coope_product
from .factory import create_scraper_for_source
from .jumbo_scraper import JumboScraper, normalize_jumbo_product
from .la_anonima_scraper import LaAnonimaScraper, normalize_la_anonima_product
from .maxiconsumo_scraper import MaxiconsumoScraper, parse_maxiconsumo_search_html
from .playwright_worker_pool import PlaywrightWorkerPool
from .vtex_region import VtexLocationTarget, VtexRegionContext

__all__ = [
    "CoopeScraper",
    "CarrefourScraper",
    "ChangoMasScraper",
    "create_scraper_for_source",
    "JumboScraper",
    "LaAnonimaScraper",
    "MaxiconsumoScraper",
    "PlaywrightWorkerPool",
    "VtexLocationTarget",
    "VtexRegionContext",
    "normalize_coope_product",
    "normalize_carrefour_product",
    "normalize_changomas_product",
    "normalize_jumbo_product",
    "normalize_la_anonima_product",
    "parse_maxiconsumo_search_html",
]
