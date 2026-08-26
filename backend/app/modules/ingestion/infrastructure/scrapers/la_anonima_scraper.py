"""La Anonima browser adapter backed by the shared Playwright worker pool."""

from __future__ import annotations

import asyncio
import logging
import sys
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urljoin

from app.modules.ingestion.domain.ports import ScraperPort

from .playwright_worker_pool import PlaywrightWorkerPool

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page


CHAIN_SLUG = "laanonima"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://www.laanonima.com.ar"
DEFAULT_RESULT_LIMIT = 5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
logger = logging.getLogger(__name__)


class LaAnonimaScraper(ScraperPort):
    """Runs bounded browser searches against La Anonima's JavaScript catalog."""

    def __init__(
        self,
        queries: list[str],
        *,
        city: str = DEFAULT_CITY,
        base_url: str = DEFAULT_BASE_URL,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        timeout_seconds: int = 25,
        max_workers: int = 2,
    ) -> None:
        cleaned_queries = [query.strip() for query in queries if len(query.strip()) >= 3]
        if not cleaned_queries:
            raise ValueError("At least one product query with three characters is required.")
        if city.strip().casefold() != DEFAULT_CITY.casefold():
            raise ValueError("La Anonima Playwright pilot only supports Comodoro Rivadavia.")
        if result_limit < 1 or result_limit > 20:
            raise ValueError("Result limit must be between 1 and 20.")
        if timeout_seconds < 1:
            raise ValueError("Timeout must be at least one second.")
        if max_workers < 1:
            raise ValueError("Worker count must be at least one.")

        self._queries = cleaned_queries
        self._city = DEFAULT_CITY
        self._base_url = base_url.rstrip("/")
        self._result_limit = result_limit
        self._timeout_ms = timeout_seconds * 1000
        self._max_workers = min(max_workers, len(cleaned_queries))

    async def scrape(self) -> list[dict]:
        """Extracts queries concurrently through reusable browser pages."""
        if _requires_dedicated_playwright_loop():
            return await asyncio.to_thread(_run_in_proactor_loop, self)
        return await self._scrape_with_pool()

    async def _scrape_with_pool(self) -> list[dict]:
        """Runs all browser resources inside the current subprocess-capable loop."""
        async with PlaywrightWorkerPool(
            max_workers=self._max_workers,
            context_options={"user_agent": USER_AGENT},
        ) as pool:
            outcomes = await asyncio.gather(
                *(pool.run(lambda page, query=query: self.search_product(page, query)) for query in self._queries),
                return_exceptions=True,
            )

        products: list[dict] = []
        errors: list[Exception] = []
        for query, outcome in zip(self._queries, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("La Anonima query %r failed: %s", query, outcome)
                errors.append(outcome)
                continue
            products.extend(outcome)
        if errors and len(errors) == len(outcomes):
            raise RuntimeError(
                f"All La Anonima browser queries failed: {errors[0]}"
            ) from errors[0]

        unique_products = {product["external_id"]: product for product in products}
        return list(unique_products.values())

    async def search_product(self, page: Page, query: str) -> list[dict]:
        """Navigates one pooled page and extracts its visible product cards."""
        await page.context.add_cookies(_location_cookies())
        page.set_default_timeout(min(self._timeout_ms, 15_000))
        response = await page.goto(
            f"{self._base_url}/buscar/{quote(query, safe='')}",
            wait_until="domcontentloaded",
            timeout=self._timeout_ms,
        )
        if response is None or response.status >= 400:
            status = response.status if response is not None else "without response"
            raise RuntimeError(f"La Anonima search returned {status}.")

        cards = page.locator("div.producto-item")
        try:
            await cards.first.wait_for(state="attached", timeout=min(self._timeout_ms, 10_000))
        except Exception:
            return []

        products = []
        for index in range(min(await cards.count(), self._result_limit)):
            product = await _extract_product_card(
                cards.nth(index),
                city=self._city,
                base_url=self._base_url,
            )
            if product is not None:
                products.append(product)
        return products


async def _extract_product_card(
    card: Locator,
    *,
    city: str,
    base_url: str,
) -> dict | None:
    link = card.locator("a[data-codigo]").first
    image = card.locator("img").first
    item = {
        "id": await card.get_attribute("id-codigo-producto")
        or await link.get_attribute("data-codigo"),
        "name": await link.get_attribute("data-nombre"),
        "brandName": await link.get_attribute("data-marca"),
        "price": await link.get_attribute("data-precio"),
        "link": await link.get_attribute("href"),
        "image": await image.get_attribute("data-src") or await image.get_attribute("src"),
        "unit": "unidad",
    }
    return normalize_la_anonima_product(item, city=city, base_url=base_url)


def normalize_la_anonima_product(
    item: dict[str, Any],
    *,
    city: str = DEFAULT_CITY,
    base_url: str = DEFAULT_BASE_URL,
) -> dict | None:
    """Transforms one browser-extracted card into the common raw contract."""
    try:
        external_id = str(item["id"]).strip()
        name = str(item["name"]).strip()
        price = Decimal(str(item["price"]).replace("$", "").replace(".", "").replace(",", "."))
        if not external_id or not name or price <= 0:
            return None
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return None

    product_link = item.get("link")
    return {
        "ean": external_id,
        "name": name,
        "brand": item.get("brandName") or "Sin marca",
        "price": float(price),
        "external_id": external_id,
        "source": CHAIN_SLUG,
        "identifier_type": "internal",
        "url": urljoin(f"{base_url.rstrip('/')}/", product_link) if product_link else None,
        "image_url": item.get("image") or None,
        "presentation": item.get("unit") or None,
        "city": city,
        "location_verified": city.casefold() == DEFAULT_CITY.casefold(),
    }


def _location_cookies() -> list[dict[str, str]]:
    """Returns the site cookies verified for La Anonima branch 47 in Comodoro."""
    values = {
        "ciudad": "Neuquen",
        "ciudad_id": "1568",
        "codigoPostal": "9000",
        "descripcionLocalidadCabezal": DEFAULT_CITY,
        "Id-Sucursal-Electro": "190",
        "Id-Sucursal-Super": "47",
        "idZonaPrecio": "8",
        "operadorLogistico": "AND",
        "provincia": "Neuquen",
        "provincia_id": "16",
        "tipoEnvioUnificado": "3",
    }
    return [
        {"name": name, "value": value, "domain": ".laanonima.com.ar", "path": "/"}
        for name, value in values.items()
    ]


def _requires_dedicated_playwright_loop() -> bool:
    """Detects Windows selector loops, which cannot launch Playwright's driver."""
    if sys.platform != "win32":
        return False
    loop = asyncio.get_running_loop()
    return "Selector" in loop.__class__.__name__


def _run_in_proactor_loop(scraper: LaAnonimaScraper) -> list[dict]:
    """Owns Playwright and its subprocesses inside one dedicated Windows loop."""
    loop_factory = getattr(asyncio, "ProactorEventLoop", None)
    if loop_factory is None:
        raise RuntimeError("Windows Proactor event loop is unavailable for Playwright.")
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        return runner.run(scraper._scrape_with_pool())
