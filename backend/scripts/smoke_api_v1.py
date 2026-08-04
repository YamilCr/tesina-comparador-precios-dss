"""Smoke test de endpoints v1 contra la base configurada por DATABASE_URL.

Este script no crea datos ni modifica el esquema. Asume que las migraciones ya
fueron aplicadas y que el seed inicial ya fue cargado.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


@dataclass(frozen=True)
class ASGIResponse:
    """Respuesta HTTP mínima devuelta por el cliente ASGI interno."""

    status_code: int
    body: bytes
    headers: dict[str, str]

    def json(self) -> Any:
        """Decodifica el cuerpo JSON de la respuesta."""
        return json.loads(self.body.decode("utf-8"))


async def asgi_request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> ASGIResponse:
    """Ejecuta una request directamente contra la app ASGI."""
    body = json.dumps(json_body or {}).encode("utf-8") if json_body is not None else b""
    headers = [(b"host", b"smoke-test")]
    if json_body is not None:
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": urlencode(query or {}, doseq=True).encode("utf-8"),
        "headers": headers,
        "client": ("smoke-test", 50000),
        "server": ("smoke-test", 80),
    }
    messages: list[dict[str, Any]] = []
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start_message.get("headers", [])
    }
    return ASGIResponse(
        status_code=start_message["status"],
        body=response_body,
        headers=response_headers,
    )


def require_status(response: ASGIResponse, expected_status: int, label: str) -> dict[str, Any]:
    """Valida status HTTP y devuelve JSON con un error claro si falla."""
    if response.status_code != expected_status:
        body = response.body.decode("utf-8", errors="replace")
        raise RuntimeError(f"{label} failed: expected {expected_status}, got {response.status_code}. Body: {body}")
    return response.json()


def require_items(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    """Valida que una respuesta tenga una lista items no vacía."""
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"{label} failed: expected non-empty items.")
    return items


async def smoke_api_v1() -> None:
    """Ejecuta verificaciones HTTP mínimas contra datos reales."""
    health = require_status(await asgi_request("GET", "/health"), 200, "health")
    if health != {"status": "ok", "service": "price-dss-backend"}:
        raise RuntimeError(f"health failed: unexpected payload {health!r}")

    products_payload = require_status(
        await asgi_request("GET", "/api/v1/catalog/products", query={"page_size": 5}),
        200,
        "catalog products",
    )
    products = require_items(products_payload, "catalog products")
    product_ids = [product["id"] for product in products[:2]]
    if len(product_ids) < 2:
        raise RuntimeError("catalog products failed: expected at least two products from seed.")

    categories = require_items(
        require_status(await asgi_request("GET", "/api/v1/catalog/categories"), 200, "catalog categories"),
        "catalog categories",
    )
    cities = require_items(
        require_status(await asgi_request("GET", "/api/v1/locations/cities"), 200, "locations cities"),
        "locations cities",
    )
    supermarkets = require_items(
        require_status(await asgi_request("GET", "/api/v1/supermarkets"), 200, "supermarkets"),
        "supermarkets",
    )
    branches = require_items(
        require_status(await asgi_request("GET", "/api/v1/branches"), 200, "branches"),
        "branches",
    )

    prices_payload = require_status(
        await asgi_request(
            "GET",
            "/api/v1/prices/current",
            query={"product_id": product_ids[0]},
        ),
        200,
        "current prices",
    )
    if prices_payload.get("count", 0) <= 0:
        raise RuntimeError("current prices failed: expected prices for seeded product.")

    basket_payload = require_status(
        await asgi_request(
            "POST",
            "/api/v1/basket/validate",
            json_body={
                "items": [
                    {"product_id": product_ids[0], "quantity": "1"},
                    {"product_id": product_ids[1], "quantity": "1"},
                ]
            },
        ),
        200,
        "basket validate",
    )
    if basket_payload.get("total_items") != 2:
        raise RuntimeError("basket validate failed: expected two items.")

    origin_city = cities[0]
    ranking_payload = require_status(
        await asgi_request(
            "POST",
            "/api/v1/decisions/ranking",
            json_body={
                "origin_latitude": origin_city["latitude"],
                "origin_longitude": origin_city["longitude"],
                "items": [
                    {"product_id": product_ids[0], "quantity": "1"},
                    {"product_id": product_ids[1], "quantity": "1"},
                ],
            },
        ),
        200,
        "decision ranking",
    )
    if not ranking_payload.get("ranking"):
        raise RuntimeError("decision ranking failed: expected at least one ranked alternative.")

    print("Smoke API v1 completed successfully.")
    print(f"Products: {len(products)}")
    print(f"Categories: {len(categories)}")
    print(f"Cities: {len(cities)}")
    print(f"Supermarkets: {len(supermarkets)}")
    print(f"Branches: {len(branches)}")
    print(f"Prices for first product: {prices_payload['count']}")
    print(f"Ranking alternatives: {len(ranking_payload['ranking'])}")


def main() -> None:
    """Punto de entrada CLI del smoke test."""
    try:
        asyncio.run(smoke_api_v1())
    except Exception as error:  # noqa: BLE001
        print(f"Smoke API v1 failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
