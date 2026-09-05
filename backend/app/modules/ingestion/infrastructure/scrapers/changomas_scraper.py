"""Chango Mas public VTEX catalog adapter for the Comodoro pilot."""

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
    get_changomas_location_target,
    resolve_vtex_region_context,
)


CHAIN_SLUG = "changomas"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://www.masonline.com.ar"
DEFAULT_RESULT_LIMIT = 10
logger = logging.getLogger(__name__)


class ChangoMasScraper(ScraperPort):
    """Extracts available Mas Online offers for a confirmed delivery region."""

    def __init__(
        self,
        queries: list[str],
        *,
        city: str = DEFAULT_CITY,
        base_url: str = DEFAULT_BASE_URL,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        timeout_seconds: int = 15,
        max_retries: int = 3,
        allow_unverified_location_fallback: bool = False,
    ) -> None:
        cleaned_queries = [query.strip() for query in queries if len(query.strip()) >= 3]
        if not cleaned_queries:
            raise ValueError("At least one product query with three characters is required.")
        if city.strip().casefold() != DEFAULT_CITY.casefold():
            raise ValueError("Chango Mas pilot only supports Comodoro Rivadavia.")
        if result_limit < 1 or result_limit > 50:
            raise ValueError("Result limit must be between 1 and 50.")
        if timeout_seconds < 1:
            raise ValueError("Timeout must be at least one second.")
        if max_retries < 1:
            raise ValueError("Max retries must be at least 1.")

        self._queries = cleaned_queries
        self._city = DEFAULT_CITY
        self._base_url = base_url.rstrip("/")
        self._result_limit = result_limit
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._allow_unverified_location_fallback = allow_unverified_location_fallback

    async def scrape(self) -> list[dict]:
        """Runs bounded searches in one location-aware HTTP session."""
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
            products = await self._search_queries_concurrently(session, context=context)

        unique_products = {product["external_id"]: product for product in products}
        return list(unique_products.values())

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
        products: list[dict] = []
        errors: list[Exception] = []
        for query, outcome in zip(self._queries, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("Chango Mas query %r failed: %s", query, outcome)
                errors.append(outcome)
                continue
            products.extend(outcome)
        if errors and len(errors) == len(outcomes):
            raise RuntimeError(f"All Chango Mas queries failed: {errors[0]}") from errors[0]
        return products

    async def search_product(
        self,
        session: aiohttp.ClientSession,
        query: str,
        *,
        context: VtexRegionContext | None = None,
    ) -> list[dict]:
        """Queries one phrase from the public VTEX catalog API."""
        encoded_query = quote(query, safe="")
        parameters = f"ft={encoded_query}&_from=0&_to={self._result_limit - 1}"
        if context is not None:
            parameters = f"{parameters}&sc={quote(context.sales_channel, safe='')}"
        data = await self._get_json_with_retry(
            session,
            f"{self._base_url}/api/catalog_system/pub/products/search?{parameters}",
            context=f"Chango Mas query={query!r}",
        )
        if not isinstance(data, list):
            logger.warning("Chango Mas returned a non-list response for query %r.", query)
            return []

        products = [
            product
            for item in data
            if (
                product := normalize_changomas_product(
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
                target=get_changomas_location_target(self._city),
                source_name="Chango Mas",
            )
        except (LookupError, VtexRegionContextError, aiohttp.ClientError) as error:
            if not self._allow_unverified_location_fallback:
                raise RuntimeError("Chango Mas location context could not be confirmed.") from error
            logger.warning("Chango Mas is using an unverified catalog location: %s", error)
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
                            f"Chango Mas rejected request with HTTP {response.status}: "
                            f"{response_text[:300]}"
                        )
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Chango Mas request failed after {self._max_retries} attempts: {context}"
        ) from last_error


def normalize_changomas_product(
    item: dict[str, Any],
    *,
    city: str = DEFAULT_CITY,
    base_url: str = DEFAULT_BASE_URL,
    location_verified: bool = False,
) -> dict | None:
    """Transforms one available VTEX offer into the shared extraction contract."""
    try:
        product_id = str(item["productId"]).strip()
        product_name = str(item["productName"]).strip()
        product_item, offer = next(
            (product_item, seller["commertialOffer"])
            for product_item in item["items"]
            for seller in product_item.get("sellers", [])
            if Decimal(str(seller.get("commertialOffer", {}).get("Price", 0))) > 0
            and Decimal(
                str(seller.get("commertialOffer", {}).get("AvailableQuantity", 0))
            )
            > 0
        )
        price = Decimal(str(offer["Price"]))
        if not product_id or not product_name or price <= 0:
            return None
    except (InvalidOperation, KeyError, StopIteration, TypeError, ValueError):
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
    product_link = item.get("link")
    if not product_link and item.get("linkText"):
        product_link = f"{item['linkText']}/p"
    ean = product_item.get("ean")

    return {
        "ean": ean or product_id,
        "name": product_name,
        "brand": item.get("brand") or None,
        "price": float(price),
        "external_id": product_id,
        "source": CHAIN_SLUG,
        "identifier_type": "gtin" if ean else "internal",
        "url": urljoin(f"{base_url.rstrip('/')}/", product_link) if product_link else None,
        "image_url": image_url,
        "presentation": None,
        "city": city,
        "location_verified": location_verified,
        "price_basis": "online_delivery_postal_code_9000" if location_verified else "catalog",
    }
