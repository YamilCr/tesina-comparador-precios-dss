"""Maxiconsumo server-rendered catalog adapter for the Comodoro pilot."""

from __future__ import annotations

import asyncio
import html
import logging
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import aiohttp

from app.modules.ingestion.domain.ports import ScraperPort

from .query_relevance import matches_query


CHAIN_SLUG = "maxiconsumo"
DEFAULT_CITY = "Comodoro Rivadavia"
DEFAULT_BASE_URL = "https://www.maxiconsumo.com/sucursal_comodoro_rivadavia"
DEFAULT_RESULT_LIMIT = 10
PRICE_BASIS = "unit_price_closed_case"
logger = logging.getLogger(__name__)


class MaxiconsumoScraper(ScraperPort):
    """Extracts Maxiconsumo products from its server-rendered Magento search page."""

    def __init__(
        self,
        queries: list[str],
        *,
        city: str = DEFAULT_CITY,
        base_url: str = DEFAULT_BASE_URL,
        result_limit: int = DEFAULT_RESULT_LIMIT,
        timeout_seconds: int = 20,
        max_retries: int = 3,
    ) -> None:
        cleaned_queries = [query.strip() for query in queries if len(query.strip()) >= 3]
        if not cleaned_queries:
            raise ValueError("At least one product query with three characters is required.")
        if city.strip().casefold() != DEFAULT_CITY.casefold():
            raise ValueError("Maxiconsumo pilot only supports Comodoro Rivadavia.")
        if result_limit < 1 or result_limit > 20:
            raise ValueError("Result limit must be between 1 and 20.")
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

    async def scrape(self) -> list[dict]:
        """Fetches bounded concurrent searches and deduplicates products by SKU."""
        timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
        connector = aiohttp.TCPConnector(limit=3)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-AR,es;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
            ),
        }
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
        ) as session:
            outcomes = await self._search_queries_concurrently(session)

        unique_products = {product["external_id"]: product for product in outcomes}
        return list(unique_products.values())

    async def _search_queries_concurrently(
        self,
        session: aiohttp.ClientSession,
    ) -> list[dict]:
        semaphore = asyncio.Semaphore(3)

        async def search(query: str) -> list[dict]:
            async with semaphore:
                return await self.search_product(session, query)

        outcomes = await asyncio.gather(
            *(search(query) for query in self._queries),
            return_exceptions=True,
        )
        products: list[dict] = []
        errors: list[Exception] = []
        for query, outcome in zip(self._queries, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("Maxiconsumo query %r failed: %s", query, outcome)
                errors.append(outcome)
                continue
            products.extend(outcome)
        if errors and len(errors) == len(outcomes):
            raise RuntimeError(f"All Maxiconsumo queries failed: {errors[0]}") from errors[0]
        return products

    async def search_product(
        self,
        session: aiohttp.ClientSession,
        query: str,
    ) -> list[dict]:
        """Downloads and parses one branch-specific catalog search."""
        body = await self._get_html_with_retry(
            session,
            f"{self._base_url}/catalogsearch/result/",
            params={"q": query},
            context=f"Maxiconsumo query={query!r}",
        )
        products = parse_maxiconsumo_search_html(
            body,
            city=self._city,
            base_url=self._base_url,
        )
        relevant = [
            product
            for product in products
            if matches_query(query=query, name=product["name"], brand=product["brand"])
        ]
        return relevant[: self._result_limit]

    async def _get_html_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        params: dict[str, str],
        context: str,
    ) -> str:
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
                        response_text = (await response.text(errors="replace")).strip()
                        raise RuntimeError(
                            f"Maxiconsumo rejected request with HTTP {response.status}: "
                            f"{response_text[:300]}"
                        )
                    return await response.text(errors="replace")
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Maxiconsumo request failed after {self._max_retries} attempts: {context}"
        ) from last_error


def parse_maxiconsumo_search_html(
    body: str,
    *,
    city: str = DEFAULT_CITY,
    base_url: str = DEFAULT_BASE_URL,
) -> list[dict]:
    """Parses Magento product cards without requiring browser execution."""
    parser = _MaxiconsumoProductParser(city=city, base_url=base_url)
    parser.feed(body)
    parser.close()
    return parser.products


class _MaxiconsumoProductParser(HTMLParser):
    def __init__(self, *, city: str, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._city = city
        self._base_url = base_url
        self._li_depth = 0
        self._card: dict[str, Any] | None = None
        self._capture: str | None = None
        self._capture_depth = 0
        self._capture_parts: list[str] = []
        self._last_price_label = ""
        self.products: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "li" and {"item", "product", "product-item"}.issubset(classes):
            if self._card is None:
                self._card = {"prices": []}
                self._li_depth = 1
                return

        if self._card is None:
            return
        if tag == "li":
            self._li_depth += 1
        if self._capture is not None:
            self._capture_depth += 1

        if "product-item-info" in classes:
            info_id = attributes.get("id") or ""
            self._card["product_id"] = info_id.removeprefix("product-item-info_") or None
        elif tag == "a" and "product-item-link" in classes:
            self._card["url"] = attributes.get("href")
            self._start_capture("name")
        elif tag == "img" and "product-image-photo" in classes:
            self._card["image_url"] = attributes.get("src") or attributes.get("data-src")
            self._card["image_alt"] = attributes.get("alt")
        elif tag == "span" and "product-sku" in classes:
            self._start_capture("sku")
        elif tag == "span" and "price-label" in classes:
            self._start_capture("price_label")
        elif tag == "span" and {"price-wrapper", "price-including-tax"}.issubset(classes):
            amount = attributes.get("data-price-amount")
            if amount:
                self._card["prices"].append((self._last_price_label, amount))

    def handle_endtag(self, tag: str) -> None:
        if self._card is None:
            return
        if self._capture is not None:
            self._capture_depth -= 1
            if self._capture_depth == 0:
                self._finish_capture()
        if tag == "li":
            self._li_depth -= 1
            if self._li_depth == 0:
                product = self._normalize_card(self._card)
                if product is not None:
                    self.products.append(product)
                self._card = None
                self._last_price_label = ""

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._capture_parts.append(data)

    def _start_capture(self, field: str) -> None:
        self._capture = field
        self._capture_depth = 1
        self._capture_parts = []

    def _finish_capture(self) -> None:
        value = " ".join("".join(self._capture_parts).split())
        if self._capture == "price_label":
            self._last_price_label = value
        elif self._card is not None:
            self._card[self._capture] = value
        self._capture = None
        self._capture_parts = []

    def _normalize_card(self, card: dict[str, Any]) -> dict | None:
        sku_match = re.search(r"(?:SKU\s*)?([\w.-]+)$", str(card.get("sku") or ""), re.I)
        external_id = sku_match.group(1) if sku_match else card.get("product_id")
        name = str(card.get("name") or card.get("image_alt") or "").strip()
        price = _select_wholesale_unit_price(card.get("prices") or [])
        if not external_id or not name or price is None or price <= 0:
            return None

        product_url = card.get("url")
        image_url = card.get("image_url")
        return {
            "ean": str(external_id),
            "name": html.unescape(name),
            "brand": None,
            "price": float(price),
            "external_id": str(external_id),
            "source": CHAIN_SLUG,
            "identifier_type": "internal",
            "url": urljoin(f"{self._base_url}/", product_url) if product_url else None,
            "image_url": urljoin(f"{self._base_url}/", image_url) if image_url else None,
            "presentation": None,
            "city": self._city,
            "location_verified": self._city.casefold() == DEFAULT_CITY.casefold(),
            "price_basis": PRICE_BASIS,
        }


def _select_wholesale_unit_price(prices: list[tuple[str, str]]) -> Decimal | None:
    preferred = [
        amount
        for label, amount in prices
        if "bulto cerrado" in label.casefold()
    ]
    for amount in (*preferred, *(amount for _, amount in prices)):
        parsed = _parse_price(amount)
        if parsed is not None and parsed > 0:
            return parsed
    return None


def _parse_price(value: str) -> Decimal | None:
    cleaned = re.sub(r"[^0-9.,]", "", html.unescape(value))
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
