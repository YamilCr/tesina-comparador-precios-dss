"""La Coope en Casa public catalog adapter for the scraping pilot."""

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import aiohttp

from app.modules.ingestion.domain.ports import ScraperPort

from .query_relevance import matches_query

CHAIN_SLUG = "lacoopeencasa"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://api.lacoopeencasa.coop"
SITE_URL = "https://www.lacoopeencasa.coop"
DEFAULT_RESULT_LIMIT = 15
logger = logging.getLogger(__name__)


class CoopeScraper(ScraperPort):
    """Extracts a small set of public La Coope en Casa search results."""

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
        """Fetches search results sequentially and deduplicates internal article codes."""
        timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
        connector = aiohttp.TCPConnector(limit=3)
        headers = {
            "Accept": "application/json",
            "Origin": SITE_URL,
            "Referer": f"{SITE_URL}/",
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
                logger.warning("La Coope query %r failed without aborting the source.", query)
                continue
            results.extend(outcome)
        return results

    async def search_product(self, session: aiohttp.ClientSession, query: str) -> list[dict]:
        """Queries the public La Coope en Casa article-search endpoint."""
        data = await self._get_json_with_retry(
            session,
            f"{self._base_url}/api/buscar/articulos",
            params={"q": query, "offset": "0", "pedido": str(self._result_limit)},
            context=f"La Coope query={query!r}",
        )
        if not isinstance(data, dict) or data.get("estado") != 1:
            logger.warning("La Coope returned an invalid search response for query %r.", query)
            return []

        items = data.get("datos")
        if not isinstance(items, list):
            return []
        products = [
            product
            for item in items[: self._result_limit]
            if (product := normalize_coope_product(item, city=self._city))
        ]
        return [
            product
            for product in products
            if matches_query(
                query=query,
                name=product["name"],
                brand=product["brand"],
            )
        ]

    async def _get_json_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        params: dict[str, str],
        context: str,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with session.get(url, params=params) as response:
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
                            f"La Coope rejected request with HTTP {response.status}: {response_text[:300]}"
                        )
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"La Coope request failed after {self._max_retries} attempts: {context}"
        ) from last_error


def normalize_coope_product(item: dict[str, Any], *, city: str = DEFAULT_CITY) -> dict | None:
    """Transforms La Coope's article payload into the pilot's raw extraction contract."""
    try:
        external_id = str(item["cod_interno"]).strip()
        name = str(item["descripcion"]).strip()
        price = Decimal(str(item["precio"]))
        if not external_id or not name or price <= 0:
            return None
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return None

    presentation = " ".join(
        part.strip()
        for part in (str(item.get("gramaje") or ""), str(item.get("unimed_desc") or ""))
        if part.strip()
    ) or None
    image_url = item.get("imagen")

    return {
        "ean": external_id,
        "name": name,
        "brand": item.get("marca_desc") or None,
        "price": float(price),
        "external_id": external_id,
        "source": CHAIN_SLUG,
        "identifier_type": "internal",
        "url": f"{SITE_URL}/articulo/{external_id}",
        "image_url": image_url if isinstance(image_url, str) else None,
        "presentation": presentation,
        "city": city,
    }
