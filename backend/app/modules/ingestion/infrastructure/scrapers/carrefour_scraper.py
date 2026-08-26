"""Carrefour public VTEX catalog adapter for the scraping pilot."""

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urljoin

import aiohttp

from app.modules.ingestion.domain.ports import ScraperPort

from .query_relevance import matches_query
from .vtex_region import (
    VtexRegionContext,
    VtexRegionContextError,
    get_carrefour_location_target,
    resolve_vtex_region_context,
)

CHAIN_SLUG = "carrefour"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://www.carrefour.com.ar"
DEFAULT_RESULT_LIMIT = 10
logger = logging.getLogger(__name__)


class CarrefourScraper(ScraperPort):
    """Extracts public Carrefour catalog search results with available offers only."""

    def __init__(
        self,
        queries: list[str],
        *,
        city: str = DEFAULT_CITY,
        base_url: str = DEFAULT_BASE_URL,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        timeout_seconds: int = 12,
        max_retries: int = 3,
        allow_unverified_location_fallback: bool = True,
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
        self._allow_unverified_location_fallback = allow_unverified_location_fallback

    async def scrape(self) -> list[dict]:
        """Fetches concurrent query results and deduplicates by Carrefour product id."""
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
            context = await self._prepare_location_context(session)
            results = await self._search_queries_concurrently(session, context=context)

        unique_results = {item["external_id"]: item for item in results}
        return list(unique_results.values())

    async def _search_queries_concurrently(
        self,
        session: aiohttp.ClientSession,
        *,
        context: VtexRegionContext | None,
    ) -> list[dict]:
        semaphore = asyncio.Semaphore(3)

        async def search(query: str) -> list[dict]:
            async with semaphore:
                return await self.search_product(session, query, context=context)

        outcomes = await asyncio.gather(
            *(search(query) for query in self._queries),
            return_exceptions=True,
        )
        results: list[dict] = []
        for query, outcome in zip(self._queries, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("Carrefour query %r failed without aborting the source.", query)
                continue
            results.extend(outcome)
        return results

    async def search_product(
        self,
        session: aiohttp.ClientSession,
        query: str,
        *,
        context: VtexRegionContext | None = None,
    ) -> list[dict]:
        """Queries Carrefour's public VTEX catalog endpoint for one phrase."""
        encoded_query = quote(query, safe="")
        query_parameters = f"ft={encoded_query}&_from=0&_to={self._result_limit - 1}"
        if context is not None:
            query_parameters = f"{query_parameters}&sc={quote(context.sales_channel, safe='')}"
        url = (
            f"{self._base_url}/api/catalog_system/pub/products/search"
            f"?{query_parameters}"
        )
        data = await self._get_json_with_retry(
            session,
            url,
            context=f"Carrefour query={query!r}",
        )
        if not isinstance(data, list):
            logger.warning("Carrefour returned a non-list response for query %r.", query)
            return []
        products = [
            product
            for item in data
            if (
                product := normalize_carrefour_product(
                    item,
                    city=self._city,
                    base_url=self._base_url,
                    location_verified=context is not None,
                )
            )
        ]
        return [
            product
            for product in products
            if matches_query(query=query, name=product["name"], brand=product["brand"])
        ]

    async def _prepare_location_context(
        self,
        session: aiohttp.ClientSession,
    ) -> VtexRegionContext | None:
        try:
            return await resolve_vtex_region_context(
                session,
                base_url=self._base_url,
                target=get_carrefour_location_target(self._city),
                source_name="Carrefour",
            )
        except (LookupError, VtexRegionContextError, aiohttp.ClientError) as error:
            if not self._allow_unverified_location_fallback:
                raise RuntimeError("Carrefour location context could not be confirmed.") from error
            logger.warning("Carrefour is using an unverified catalog location: %s", error)
            return None

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
                            f"Carrefour rejected request with HTTP {response.status}: "
                            f"{response_text[:300]}"
                        )
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Carrefour request failed after {self._max_retries} attempts: {context}"
        ) from last_error


def normalize_carrefour_product(
    item: dict[str, Any],
    *,
    city: str = DEFAULT_CITY,
    base_url: str = DEFAULT_BASE_URL,
    location_verified: bool = False,
) -> dict | None:
    """Transforms a VTEX product with stock into the common raw extraction contract."""
    try:
        product_id = str(item["productId"]).strip()
        product_name = str(item["productName"]).strip()
        sku = item["items"][0]
        offer = next(
            seller["commertialOffer"]
            for seller in sku["sellers"]
            if Decimal(str(seller.get("commertialOffer", {}).get("Price", 0))) > 0
            and Decimal(str(seller.get("commertialOffer", {}).get("AvailableQuantity", 0))) > 0
        )
        price = Decimal(str(offer["Price"]))
        if not product_id or not product_name or price <= 0:
            return None
    except (IndexError, InvalidOperation, KeyError, StopIteration, TypeError, ValueError):
        return None

    images = sku.get("images") or []
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
    ean = sku.get("ean")

    return {
        "ean": ean or product_id,
        "name": product_name,
        "brand": item.get("brand") or None,
        "price": float(price),
        "external_id": product_id,
        "source": CHAIN_SLUG,
        "identifier_type": "gtin" if ean else "internal",
        "url": product_url,
        "image_url": image_url,
        "presentation": None,
        "city": city,
        "location_verified": location_verified,
    }
