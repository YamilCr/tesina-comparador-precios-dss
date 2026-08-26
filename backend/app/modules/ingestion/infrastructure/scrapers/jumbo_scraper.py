"""Jumbo public catalog adapter used by the single-chain scraping pilot."""

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urljoin

import aiohttp

from app.modules.ingestion.domain.ports import ScraperPort

CHAIN_SLUG = "jumbo"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://www.jumbo.com.ar"
DEFAULT_RESULT_LIMIT = 10
logger = logging.getLogger(__name__)


class JumboScraper(ScraperPort):
    """Extracts a small set of public Jumbo catalog search results."""

    def __init__(
        self,
        queries: list[str],
        *,
        city: str = DEFAULT_CITY,
        base_url: str = DEFAULT_BASE_URL,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        timeout_seconds: int = 12,
        max_retries: int = 3,
    ) -> None:
        cleaned_queries = [query.strip() for query in queries if query.strip()]
        if not cleaned_queries:
            raise ValueError("At least one product query is required.")
        if not city.strip():
            raise ValueError("City cannot be empty.")
        if result_limit < 1 or result_limit > 50:
            raise ValueError("Result limit must be between 1 and 50.")
        if max_retries < 1:
            raise ValueError("Max retries must be at least 1.")

        self._queries = cleaned_queries
        self._city = city.strip()
        self._base_url = base_url.rstrip("/")
        self._result_limit = result_limit
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def scrape(self) -> list[dict]:
        """Fetches and validates catalog matches, deduplicated by Jumbo product id."""
        timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
        connector = aiohttp.TCPConnector(limit=3)
        headers = {
            "Accept": "application/json",
            "User-Agent": "dss-price-comparator-pilot/0.1 (+educational-demo)",
        }
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
        ) as session:
            results = await self._search_queries_concurrently(session)

        unique_results = {item["external_id"]: item for item in results}
        return list(unique_results.values())

    async def _search_queries_concurrently(
        self,
        session: aiohttp.ClientSession,
    ) -> list[dict]:
        """Bounds simultaneous requests while preserving partial query results."""
        semaphore = asyncio.Semaphore(3)

        async def search(query: str) -> list[dict]:
            async with semaphore:
                return await self.search_product(session, query)

        outcomes = await asyncio.gather(
            *(search(query) for query in self._queries),
            return_exceptions=True,
        )
        results: list[dict] = []
        for query, outcome in zip(self._queries, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("Jumbo query %r failed without aborting the source.", query)
                continue
            results.extend(outcome)
        return results

    async def search_product(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        """Queries Jumbo's public catalog endpoint for one product phrase."""
        encoded_query = quote(query, safe="")
        url = (
            f"{self._base_url}/api/catalog_system/pub/products/search"
            f"?ft={encoded_query}&_from=0&_to={self._result_limit - 1}"
        )
        data = await self._get_json_with_retry(
            session,
            url,
            context=f"Jumbo query={query!r}",
        )
        if not isinstance(data, list):
            logger.warning("Jumbo returned a non-list response for query %r.", query)
            return []
        return [
            product
            for item in data
            if (product := normalize_jumbo_product(item, city=self._city, base_url=self._base_url))
        ]

    async def _get_json_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        context: str,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with session.get(url) as response:
                    if response.status == 429 or response.status >= 500:
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=f"Retryable HTTP status for {context}",
                            headers=response.headers,
                        )
                    if response.status >= 400:
                        response_text = (await response.text()).strip().replace("\n", " ")
                        raise RuntimeError(
                            f"Jumbo rejected request with HTTP {response.status}: {response_text[:300]}"
                        )
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(f"Jumbo request failed after {self._max_retries} attempts: {context}") from last_error


def normalize_jumbo_product(
    item: dict[str, Any],
    *,
    city: str = DEFAULT_CITY,
    base_url: str = DEFAULT_BASE_URL,
) -> dict | None:
    """Transforms Jumbo's catalog payload into the pilot's raw extraction contract."""
    try:
        product_id = str(item["productId"]).strip()
        product_name = str(item["productName"]).strip()
        product_item = item["items"][0]
        seller = product_item["sellers"][0]
        offer = seller["commertialOffer"]
        price = Decimal(str(offer["Price"]))
        if not product_id or not product_name or price <= 0:
            return None
    except (IndexError, InvalidOperation, KeyError, TypeError, ValueError):
        return None

    images = product_item.get("images") or []
    image_url = next(
        (
            image.get("imageUrl")
            for image in images
            if isinstance(image, dict) and isinstance(image.get("imageUrl"), str)
        ),
        None,
    )
    link_text = item.get("linkText")
    product_url = urljoin(f"{base_url.rstrip('/')}/", f"{link_text}/p") if link_text else None

    return {
        "ean": product_item.get("ean") or product_id,
        "name": product_name,
        "brand": item.get("brand") or None,
        "price": float(price),
        "external_id": product_id,
        "source": CHAIN_SLUG,
        "identifier_type": "gtin",
        "url": product_url,
        "image_url": image_url,
        "presentation": None,
        "city": city,
    }
