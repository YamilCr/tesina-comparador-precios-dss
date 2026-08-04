"""Fixtures de integración con SQLite async y datos mínimos reales."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import get_unit_of_work
from app.main import app
from app.modules.catalog.infrastructure.persistence import (
    BrandModel,
    ProductCategoryModel,
    ProductModel,
    ProductSourceModel,
)
from app.modules.prices.infrastructure.persistence import PriceModel
from app.modules.supermarkets.infrastructure.persistence import (
    BranchModel,
    CityModel,
    ProvinceModel,
    SupermarketModel,
)
from app.shared.infrastructure.sqlalchemy_base import Base
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

# Importa todos los modelos para que Base.metadata tenga el esquema completo.
import app.shared.infrastructure.model_registry as _model_registry  # noqa: F401


@dataclass(frozen=True)
class IntegrationSeedData:
    """Identificadores estables del dataset mínimo usado por tests reales."""

    province_id: UUID = UUID("10000000-0000-0000-0000-000000000001")
    city_id: UUID = UUID("10000000-0000-0000-0000-000000000002")
    la_anonima_id: UUID = UUID("10000000-0000-0000-0000-000000000011")
    carrefour_id: UUID = UUID("10000000-0000-0000-0000-000000000012")
    la_branch_id: UUID = UUID("10000000-0000-0000-0000-000000000021")
    carrefour_branch_id: UUID = UUID("10000000-0000-0000-0000-000000000022")
    category_id: UUID = UUID("10000000-0000-0000-0000-000000000031")
    brand_coca_id: UUID = UUID("10000000-0000-0000-0000-000000000032")
    brand_serenisima_id: UUID = UUID("10000000-0000-0000-0000-000000000033")
    coca_product_id: UUID = UUID("10000000-0000-0000-0000-000000000041")
    milk_product_id: UUID = UUID("10000000-0000-0000-0000-000000000042")
    la_coca_source_id: UUID = UUID("10000000-0000-0000-0000-000000000051")
    carrefour_coca_source_id: UUID = UUID("10000000-0000-0000-0000-000000000052")
    la_milk_source_id: UUID = UUID("10000000-0000-0000-0000-000000000053")
    carrefour_milk_source_id: UUID = UUID("10000000-0000-0000-0000-000000000054")
    la_coca_current_price_id: UUID = UUID("10000000-0000-0000-0000-000000000061")
    la_coca_old_price_id: UUID = UUID("10000000-0000-0000-0000-000000000062")
    carrefour_coca_price_id: UUID = UUID("10000000-0000-0000-0000-000000000063")
    la_milk_price_id: UUID = UUID("10000000-0000-0000-0000-000000000064")
    carrefour_milk_price_id: UUID = UUID("10000000-0000-0000-0000-000000000065")
    unavailable_price_id: UUID = UUID("10000000-0000-0000-0000-000000000066")

    observed_at: datetime = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    older_observed_at: datetime = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ASGIResponse:
    """Respuesta mínima obtenida al invocar la aplicación ASGI en memoria."""

    status_code: int
    body: bytes
    headers: dict[str, str]

    def json(self) -> Any:
        """Decodifica el cuerpo JSON de la respuesta."""
        return json.loads(self.body.decode("utf-8"))


@pytest.fixture
def seed_data() -> IntegrationSeedData:
    """Expone los identificadores del dataset real de integración."""
    return IntegrationSeedData()


async def _seed_sqlite_database(
    session_factory: async_sessionmaker[AsyncSession],
    seed: IntegrationSeedData,
) -> None:
    """Carga datos mínimos coherentes en una base SQLite temporal."""
    async with session_factory() as session:
        session.add_all(
            [
                ProvinceModel(
                    id=seed.province_id,
                    nombre="Chubut",
                    codigo_iso="AR-U",
                ),
                SupermarketModel(
                    id=seed.la_anonima_id,
                    nombre="La Anónima",
                    sitio_web=None,
                    activo=True,
                ),
                SupermarketModel(
                    id=seed.carrefour_id,
                    nombre="Carrefour",
                    sitio_web=None,
                    activo=True,
                ),
                ProductCategoryModel(
                    id=seed.category_id,
                    nombre="Bebidas",
                    descripcion="Bebidas de prueba para integración.",
                    activo=True,
                ),
                BrandModel(
                    id=seed.brand_coca_id,
                    nombre="Coca Cola",
                    descripcion=None,
                    activo=True,
                ),
                BrandModel(
                    id=seed.brand_serenisima_id,
                    nombre="La Serenísima",
                    descripcion=None,
                    activo=True,
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                CityModel(
                    id=seed.city_id,
                    provincia_id=seed.province_id,
                    nombre="Comodoro Rivadavia",
                    codigo_postal="9000",
                    latitud=Decimal("-45.864100"),
                    longitud=Decimal("-67.496600"),
                ),
                ProductModel(
                    id=seed.coca_product_id,
                    categoria_id=seed.category_id,
                    marca_id=seed.brand_coca_id,
                    nombre_normalizado="Coca Cola 2.25 L",
                    unidad_medida="L",
                    contenido_neto=Decimal("2.250"),
                    codigo_interno="BEB-COCA-225",
                    activo=True,
                ),
                ProductModel(
                    id=seed.milk_product_id,
                    categoria_id=seed.category_id,
                    marca_id=seed.brand_serenisima_id,
                    nombre_normalizado="Leche Entera 1 L",
                    unidad_medida="L",
                    contenido_neto=Decimal("1.000"),
                    codigo_interno="LAC-LECHE-001",
                    activo=True,
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                BranchModel(
                    id=seed.la_branch_id,
                    supermercado_id=seed.la_anonima_id,
                    ciudad_id=seed.city_id,
                    nombre="Centro",
                    direccion="San Martín 500",
                    latitud=Decimal("-45.864500"),
                    longitud=Decimal("-67.482000"),
                    activo=True,
                ),
                BranchModel(
                    id=seed.carrefour_branch_id,
                    supermercado_id=seed.carrefour_id,
                    ciudad_id=seed.city_id,
                    nombre="Comodoro",
                    direccion="Av. Hipólito Yrigoyen 2600",
                    latitud=Decimal("-45.875000"),
                    longitud=Decimal("-67.510000"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=seed.la_coca_source_id,
                    producto_id=seed.coca_product_id,
                    supermercado_id=seed.la_anonima_id,
                    nombre_original="Coca Cola Sabor Original 2.25L",
                    codigo_externo="LA-COCA-225",
                    unidad_original="L",
                    confianza_match=Decimal("0.950"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=seed.carrefour_coca_source_id,
                    producto_id=seed.coca_product_id,
                    supermercado_id=seed.carrefour_id,
                    nombre_original="Gaseosa Coca Cola 2,25 L",
                    codigo_externo="CAR-COCA-225",
                    unidad_original="L",
                    confianza_match=Decimal("0.950"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=seed.la_milk_source_id,
                    producto_id=seed.milk_product_id,
                    supermercado_id=seed.la_anonima_id,
                    nombre_original="Leche Entera La Serenísima 1L",
                    codigo_externo="LA-LECHE-001",
                    unidad_original="L",
                    confianza_match=Decimal("0.950"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=seed.carrefour_milk_source_id,
                    producto_id=seed.milk_product_id,
                    supermercado_id=seed.carrefour_id,
                    nombre_original="Leche Entera La Serenísima 1 L",
                    codigo_externo="CAR-LECHE-001",
                    unidad_original="L",
                    confianza_match=Decimal("0.950"),
                    activo=True,
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                PriceModel(
                    id=seed.la_coca_current_price_id,
                    producto_fuente_id=seed.la_coca_source_id,
                    sucursal_id=seed.la_branch_id,
                    precio=Decimal("2600.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=seed.la_coca_old_price_id,
                    producto_fuente_id=seed.la_coca_source_id,
                    sucursal_id=seed.la_branch_id,
                    precio=Decimal("2700.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.older_observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=seed.carrefour_coca_price_id,
                    producto_fuente_id=seed.carrefour_coca_source_id,
                    sucursal_id=seed.carrefour_branch_id,
                    precio=Decimal("2500.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=seed.la_milk_price_id,
                    producto_fuente_id=seed.la_milk_source_id,
                    sucursal_id=seed.la_branch_id,
                    precio=Decimal("1450.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=seed.carrefour_milk_price_id,
                    producto_fuente_id=seed.carrefour_milk_source_id,
                    sucursal_id=seed.carrefour_branch_id,
                    precio=Decimal("1500.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=seed.unavailable_price_id,
                    producto_fuente_id=seed.carrefour_coca_source_id,
                    sucursal_id=seed.carrefour_branch_id,
                    precio=Decimal("1.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed.observed_at,
                    disponible=False,
                    promocion=True,
                ),
            ]
        )
        await session.commit()


@pytest_asyncio.fixture
async def sqlite_session_factory(
    tmp_path: Path,
    seed_data: IntegrationSeedData,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Crea una base SQLite temporal con el schema real y datos mínimos."""
    database_path = tmp_path / "price_dss_integration.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await _seed_sqlite_database(session_factory, seed_data)

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.fixture
def sqlite_uow_override(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], None]:
    """Instala un UnitOfWork SQLAlchemy real para endpoints HTTP."""
    app.dependency_overrides[get_unit_of_work] = lambda: SQLAlchemyUnitOfWork(
        sqlite_session_factory
    )
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def asgi_request() -> Callable[..., Any]:
    """Devuelve un cliente ASGI mínimo para invocar FastAPI sin dependencias externas."""

    async def _request(
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> ASGIResponse:
        body = json.dumps(json_body or {}).encode("utf-8") if json_body is not None else b""
        query_string = urlencode(query or {}, doseq=True).encode("utf-8")
        headers = [(b"host", b"testserver")]
        if json_body is not None:
            headers.append((b"content-type", b"application/json"))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string,
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
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

        start_message = next(
            message for message in messages if message["type"] == "http.response.start"
        )
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

    return _request
