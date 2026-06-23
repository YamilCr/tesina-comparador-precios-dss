"""Carga datos iniciales idempotentes para probar el DSS sin scraping."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.catalog.infrastructure.persistence import (  # noqa: E402
    BrandModel,
    ProductCategoryModel,
    ProductModel,
    ProductSourceModel,
)
from app.modules.prices.infrastructure.persistence import PriceModel  # noqa: E402
from app.modules.supermarkets.infrastructure.persistence import (  # noqa: E402
    BranchModel,
    CityModel,
    ProvinceModel,
    SupermarketModel,
)
from app.shared.infrastructure.database import create_database_engine  # noqa: E402
from app.shared.infrastructure.settings import get_settings  # noqa: E402


SEED_OBSERVED_AT = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

SUPERMARKETS = (
    {"name": "La Anónima", "website_url": None},
    {"name": "Carrefour", "website_url": None},
    {"name": "Chango Más", "website_url": None},
    {"name": "Jumbo", "website_url": None},
)

BRANCHES = (
    {
        "key": "la_anonima_centro",
        "supermarket": "La Anónima",
        "city": "Comodoro Rivadavia",
        "name": "Centro",
        "address": "San Martín 500",
        "latitude": Decimal("-45.8645"),
        "longitude": Decimal("-67.4820"),
    },
    {
        "key": "carrefour_comodoro",
        "supermarket": "Carrefour",
        "city": "Comodoro Rivadavia",
        "name": "Comodoro",
        "address": "Av. Hipólito Yrigoyen 2600",
        "latitude": Decimal("-45.8750"),
        "longitude": Decimal("-67.5100"),
    },
    {
        "key": "changomas_comodoro",
        "supermarket": "Chango Más",
        "city": "Comodoro Rivadavia",
        "name": "Comodoro",
        "address": "Av. Polonia 1200",
        "latitude": Decimal("-45.8460"),
        "longitude": Decimal("-67.5000"),
    },
    {
        "key": "la_anonima_rada_tilly",
        "supermarket": "La Anónima",
        "city": "Rada Tilly",
        "name": "Rada Tilly",
        "address": "Av. Moyano 900",
        "latitude": Decimal("-45.9250"),
        "longitude": Decimal("-67.5550"),
    },
)

PRODUCTS = (
    {
        "internal_code": "BEB-COCA-225",
        "normalized_name": "Coca Cola 2.25 L",
        "category": "Bebidas",
        "brand": "Coca Cola",
        "unit_measure": "L",
        "net_content": Decimal("2.25"),
        "source_suffix": "COCA-225",
        "source_names": {
            "La Anónima": "Coca Cola Sabor Original 2.25L",
            "Carrefour": "Gaseosa Coca Cola 2,25 L",
            "Chango Más": "Coca-Cola Original 2.25 Litros",
            "Jumbo": "Coca Cola Original 2.25L",
        },
    },
    {
        "internal_code": "LAC-LECHE-001",
        "normalized_name": "Leche Entera 1 L",
        "category": "Lácteos",
        "brand": "La Serenísima",
        "unit_measure": "L",
        "net_content": Decimal("1"),
        "source_suffix": "LECHE-001",
        "source_names": {},
    },
    {
        "internal_code": "ALM-ARROZ-001",
        "normalized_name": "Arroz Largo Fino 1 Kg",
        "category": "Almacén",
        "brand": "Marolio",
        "unit_measure": "KG",
        "net_content": Decimal("1"),
        "source_suffix": "ARROZ-001",
        "source_names": {},
    },
    {
        "internal_code": "LIM-LAV-001",
        "normalized_name": "Lavandina 1 L",
        "category": "Limpieza",
        "brand": "Ayudín",
        "unit_measure": "L",
        "net_content": Decimal("1"),
        "source_suffix": "LAV-001",
        "source_names": {},
    },
    {
        "internal_code": "HIG-PAPEL-004",
        "normalized_name": "Papel Higiénico 4 Rollos",
        "category": "Higiene personal",
        "brand": "Elite",
        "unit_measure": "PACK",
        "net_content": Decimal("4"),
        "source_suffix": "PAPEL-004",
        "source_names": {},
    },
)

SUPERMARKET_CODE_PREFIXES = {
    "La Anónima": "LA",
    "Carrefour": "CAR",
    "Chango Más": "CHA",
    "Jumbo": "JUM",
}

PRICE_DATA = {
    "la_anonima_centro": {
        "BEB-COCA-225": Decimal("2600"),
        "LAC-LECHE-001": Decimal("1450"),
        "ALM-ARROZ-001": Decimal("1800"),
        "LIM-LAV-001": Decimal("1200"),
        "HIG-PAPEL-004": Decimal("3200"),
    },
    "carrefour_comodoro": {
        "BEB-COCA-225": Decimal("2550"),
        "LAC-LECHE-001": Decimal("1500"),
        "ALM-ARROZ-001": Decimal("1750"),
        "LIM-LAV-001": Decimal("1150"),
        "HIG-PAPEL-004": Decimal("3150"),
    },
    "changomas_comodoro": {
        "BEB-COCA-225": Decimal("2500"),
        "LAC-LECHE-001": Decimal("1420"),
        "ALM-ARROZ-001": Decimal("1700"),
        "LIM-LAV-001": Decimal("1100"),
        "HIG-PAPEL-004": Decimal("3300"),
    },
    "la_anonima_rada_tilly": {
        "BEB-COCA-225": Decimal("2700"),
        "LAC-LECHE-001": Decimal("1480"),
        "ALM-ARROZ-001": Decimal("1850"),
        "LIM-LAV-001": Decimal("1250"),
        "HIG-PAPEL-004": Decimal("3400"),
    },
}


@dataclass
class SeedCounts:
    """Acumula registros creados y encontrados para un tipo de dato."""

    created: int = 0
    found: int = 0


@dataclass
class SeedSummary:
    """Agrupa el resumen de ejecución sin exponer datos sensibles."""

    counts: dict[str, SeedCounts] = field(
        default_factory=lambda: {
            "provinces": SeedCounts(),
            "cities": SeedCounts(),
            "supermarkets": SeedCounts(),
            "branches": SeedCounts(),
            "categories": SeedCounts(),
            "brands": SeedCounts(),
            "products": SeedCounts(),
            "product_sources": SeedCounts(),
            "prices": SeedCounts(),
        }
    )

    def record(self, resource: str, created: bool) -> None:
        """Registra si un dato se creó o ya existía."""
        if created:
            self.counts[resource].created += 1
        else:
            self.counts[resource].found += 1

    def print(self) -> None:
        """Imprime el resumen de resultados de forma legible."""
        labels = {
            "provinces": "Provincias",
            "cities": "Ciudades",
            "supermarkets": "Supermercados",
            "branches": "Sucursales",
            "categories": "Categorías",
            "brands": "Marcas",
            "products": "Productos",
            "product_sources": "Productos fuente",
            "prices": "Precios",
        }
        print("Seed completed successfully.")
        for resource, label in labels.items():
            count = self.counts[resource]
            print(f"- {label}: creados={count.created}, encontrados={count.found}")


async def get_or_create_province(
    session: AsyncSession,
    name: str,
    iso_code: str | None,
) -> tuple[ProvinceModel, bool]:
    """Busca una provincia por nombre o crea el registro inicial."""
    province = await session.scalar(select(ProvinceModel).where(ProvinceModel.nombre == name))
    if province is not None:
        return province, False

    province = ProvinceModel(id=uuid4(), nombre=name, codigo_iso=iso_code)
    session.add(province)
    await session.flush()
    return province, True


async def get_or_create_city(
    session: AsyncSession,
    province_id: UUID,
    name: str,
    latitude: Decimal,
    longitude: Decimal,
) -> tuple[CityModel, bool]:
    """Busca una ciudad por provincia y nombre o crea el registro inicial."""
    city = await session.scalar(
        select(CityModel).where(
            CityModel.provincia_id == province_id,
            CityModel.nombre == name,
        )
    )
    if city is not None:
        return city, False

    city = CityModel(
        id=uuid4(),
        provincia_id=province_id,
        nombre=name,
        latitud=latitude,
        longitud=longitude,
    )
    session.add(city)
    await session.flush()
    return city, True


async def get_or_create_supermarket(
    session: AsyncSession,
    name: str,
    website_url: str | None,
) -> tuple[SupermarketModel, bool]:
    """Busca un supermercado por nombre o crea el registro inicial."""
    supermarket = await session.scalar(
        select(SupermarketModel).where(SupermarketModel.nombre == name)
    )
    if supermarket is not None:
        return supermarket, False

    supermarket = SupermarketModel(
        id=uuid4(),
        nombre=name,
        sitio_web=website_url,
        activo=True,
    )
    session.add(supermarket)
    await session.flush()
    return supermarket, True


async def get_or_create_branch(
    session: AsyncSession,
    supermarket_id: UUID,
    city_id: UUID,
    name: str,
    address: str,
    latitude: Decimal,
    longitude: Decimal,
) -> tuple[BranchModel, bool]:
    """Busca una sucursal por su clave natural o crea el registro inicial."""
    branch = await session.scalar(
        select(BranchModel).where(
            BranchModel.supermercado_id == supermarket_id,
            BranchModel.nombre == name,
            BranchModel.direccion == address,
        )
    )
    if branch is not None:
        return branch, False

    branch = BranchModel(
        id=uuid4(),
        supermercado_id=supermarket_id,
        ciudad_id=city_id,
        nombre=name,
        direccion=address,
        latitud=latitude,
        longitud=longitude,
        activo=True,
    )
    session.add(branch)
    await session.flush()
    return branch, True


async def get_or_create_category(
    session: AsyncSession,
    name: str,
) -> tuple[ProductCategoryModel, bool]:
    """Busca una categoría por nombre o crea el registro inicial."""
    category = await session.scalar(
        select(ProductCategoryModel).where(ProductCategoryModel.nombre == name)
    )
    if category is not None:
        return category, False

    category = ProductCategoryModel(id=uuid4(), nombre=name, activo=True)
    session.add(category)
    await session.flush()
    return category, True


async def get_or_create_brand(session: AsyncSession, name: str) -> tuple[BrandModel, bool]:
    """Busca una marca por nombre o crea el registro inicial."""
    brand = await session.scalar(select(BrandModel).where(BrandModel.nombre == name))
    if brand is not None:
        return brand, False

    brand = BrandModel(id=uuid4(), nombre=name, activo=True)
    session.add(brand)
    await session.flush()
    return brand, True


async def get_or_create_product(
    session: AsyncSession,
    category_id: UUID,
    brand_id: UUID,
    normalized_name: str,
    unit_measure: str,
    net_content: Decimal,
    internal_code: str,
) -> tuple[ProductModel, bool]:
    """Busca un producto por código interno o crea el registro inicial."""
    product = await session.scalar(
        select(ProductModel).where(ProductModel.codigo_interno == internal_code)
    )
    if product is not None:
        return product, False

    product = ProductModel(
        id=uuid4(),
        categoria_id=category_id,
        marca_id=brand_id,
        nombre_normalizado=normalized_name,
        unidad_medida=unit_measure,
        contenido_neto=net_content,
        codigo_interno=internal_code,
        activo=True,
    )
    session.add(product)
    await session.flush()
    return product, True


async def get_or_create_product_source(
    session: AsyncSession,
    product_id: UUID,
    supermarket_id: UUID,
    original_name: str,
    external_code: str,
) -> tuple[ProductSourceModel, bool]:
    """Busca una publicación por supermercado y código externo o la crea."""
    product_source = await session.scalar(
        select(ProductSourceModel).where(
            ProductSourceModel.supermercado_id == supermarket_id,
            ProductSourceModel.codigo_externo == external_code,
        )
    )
    if product_source is not None:
        return product_source, False

    product_source = ProductSourceModel(
        id=uuid4(),
        producto_id=product_id,
        supermercado_id=supermarket_id,
        nombre_original=original_name,
        codigo_externo=external_code,
        confianza_match=Decimal("0.95"),
        activo=True,
    )
    session.add(product_source)
    await session.flush()
    return product_source, True


async def get_or_create_price(
    session: AsyncSession,
    product_source_id: UUID,
    branch_id: UUID,
    amount: Decimal,
) -> tuple[PriceModel, bool]:
    """Busca un precio por fuente, sucursal y fecha fija o crea el histórico."""
    price = await session.scalar(
        select(PriceModel).where(
            PriceModel.producto_fuente_id == product_source_id,
            PriceModel.sucursal_id == branch_id,
            PriceModel.fecha_relevamiento == SEED_OBSERVED_AT,
        )
    )
    if price is not None:
        return price, False

    price = PriceModel(
        id=uuid4(),
        producto_fuente_id=product_source_id,
        sucursal_id=branch_id,
        precio=amount,
        moneda="ARS",
        fecha_relevamiento=SEED_OBSERVED_AT,
        disponible=True,
        promocion=False,
        created_at=SEED_OBSERVED_AT,
    )
    session.add(price)
    await session.flush()
    return price, True


async def seed_initial_data() -> None:
    """Carga el conjunto mínimo de datos de prueba y muestra su resumen."""
    summary = SeedSummary()
    engine = create_database_engine(get_settings())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            async with session.begin():
                province, created = await get_or_create_province(session, "Chubut", "AR-U")
                summary.record("provinces", created)

                cities: dict[str, CityModel] = {}
                for name, latitude, longitude in (
                    ("Comodoro Rivadavia", Decimal("-45.8641"), Decimal("-67.4966")),
                    ("Rada Tilly", Decimal("-45.9269"), Decimal("-67.5542")),
                ):
                    city, created = await get_or_create_city(
                        session,
                        province.id,
                        name,
                        latitude,
                        longitude,
                    )
                    cities[name] = city
                    summary.record("cities", created)

                supermarkets: dict[str, SupermarketModel] = {}
                for supermarket_data in SUPERMARKETS:
                    supermarket, created = await get_or_create_supermarket(
                        session,
                        supermarket_data["name"],
                        supermarket_data["website_url"],
                    )
                    supermarkets[supermarket_data["name"]] = supermarket
                    summary.record("supermarkets", created)

                branches: dict[str, BranchModel] = {}
                branch_supermarkets: dict[str, str] = {}
                for branch_data in BRANCHES:
                    branch, created = await get_or_create_branch(
                        session,
                        supermarkets[branch_data["supermarket"]].id,
                        cities[branch_data["city"]].id,
                        branch_data["name"],
                        branch_data["address"],
                        branch_data["latitude"],
                        branch_data["longitude"],
                    )
                    branches[branch_data["key"]] = branch
                    branch_supermarkets[branch_data["key"]] = branch_data["supermarket"]
                    summary.record("branches", created)

                categories: dict[str, ProductCategoryModel] = {}
                for category_name in ("Bebidas", "Lácteos", "Almacén", "Limpieza", "Higiene personal"):
                    category, created = await get_or_create_category(session, category_name)
                    categories[category_name] = category
                    summary.record("categories", created)

                brands: dict[str, BrandModel] = {}
                for brand_name in ("Coca Cola", "La Serenísima", "Sancor", "Marolio", "Ayudín", "Elite"):
                    brand, created = await get_or_create_brand(session, brand_name)
                    brands[brand_name] = brand
                    summary.record("brands", created)

                products: dict[str, ProductModel] = {}
                product_definitions: dict[str, dict[str, object]] = {}
                for product_data in PRODUCTS:
                    product, created = await get_or_create_product(
                        session,
                        categories[product_data["category"]].id,
                        brands[product_data["brand"]].id,
                        product_data["normalized_name"],
                        product_data["unit_measure"],
                        product_data["net_content"],
                        product_data["internal_code"],
                    )
                    products[product_data["internal_code"]] = product
                    product_definitions[product_data["internal_code"]] = product_data
                    summary.record("products", created)

                product_sources: dict[tuple[str, str], ProductSourceModel] = {}
                for internal_code, product in products.items():
                    product_data = product_definitions[internal_code]
                    for supermarket_name, supermarket in supermarkets.items():
                        source_name = product_data["source_names"].get(
                            supermarket_name,
                            product_data["normalized_name"],
                        )
                        external_code = (
                            f"{SUPERMARKET_CODE_PREFIXES[supermarket_name]}-"
                            f"{product_data['source_suffix']}"
                        )
                        product_source, created = await get_or_create_product_source(
                            session,
                            product.id,
                            supermarket.id,
                            source_name,
                            external_code,
                        )
                        product_sources[(internal_code, supermarket_name)] = product_source
                        summary.record("product_sources", created)

                for branch_key, branch_prices in PRICE_DATA.items():
                    branch = branches[branch_key]
                    supermarket_name = branch_supermarkets[branch_key]
                    for internal_code, amount in branch_prices.items():
                        _, created = await get_or_create_price(
                            session,
                            product_sources[(internal_code, supermarket_name)].id,
                            branch.id,
                            amount,
                        )
                        summary.record("prices", created)
    finally:
        await engine.dispose()

    summary.print()


if __name__ == "__main__":
    asyncio.run(seed_initial_data())
