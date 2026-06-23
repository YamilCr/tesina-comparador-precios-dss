"""Adaptador HTTP de lectura y comparaciÃ³n para la interfaz DSS."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.infrastructure.persistence.sqlalchemy_models import (
    BrandModel,
    ProductCategoryModel,
    ProductModel,
    ProductSourceModel,
)
from app.modules.decision.domain.entities import Alternative
from app.modules.decision.domain.services import WeightedSumModel
from app.modules.decision.domain.value_objects import CriteriaWeights
from app.modules.geo.domain.services import HaversineDistanceService
from app.modules.geo.domain.value_objects import GeoPoint
from app.modules.prices.infrastructure.persistence.sqlalchemy_models import PriceModel
from app.modules.supermarkets.infrastructure.persistence.sqlalchemy_models import (
    BranchModel,
    CityModel,
    ProvinceModel,
    SupermarketModel,
)
from app.shared.infrastructure.database import get_async_session


router = APIRouter(prefix="/api/v1", tags=["DSS"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]


class BasketLineRequest(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class RankingWeightsRequest(BaseModel):
    price: Decimal = Decimal("0.6")
    distance: Decimal = Decimal("0.3")
    saving: Decimal = Decimal("0.1")

    @model_validator(mode="after")
    def validate_weights(self) -> "RankingWeightsRequest":
        weights = (self.price, self.distance, self.saving)
        if any(weight < 0 for weight in weights):
            raise ValueError("Los pesos no pueden ser negativos.")
        if sum(weights, Decimal("0")) != Decimal("1"):
            raise ValueError("Los pesos deben sumar exactamente 1.")
        return self


class RankingRequest(BaseModel):
    city_id: UUID
    items: list[BasketLineRequest] = Field(min_length=1, max_length=100)
    weights: RankingWeightsRequest = Field(default_factory=RankingWeightsRequest)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "RankingRequest":
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada producto debe aparecer una sola vez en la canasta.")
        return self


def _decimal(value: Decimal | None, places: int | None = None) -> str | None:
    """Serializa importes sin perder precisiÃ³n en JSON."""
    if value is None:
        return None
    if places is not None:
        return f"{value:.{places}f}"
    return format(value, "f")


def _pagination(page: int, page_size: int, total: int) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "total": total}


def _branch_payload(branch: BranchModel, supermarket_name: str, city_name: str | None = None) -> dict:
    return {
        "id": str(branch.id),
        "nombre": branch.nombre,
        "direccion": branch.direccion,
        "supermercado": supermarket_name,
        "ciudad": city_name,
        "latitud": float(branch.latitud),
        "longitud": float(branch.longitud),
    }


def _latest_prices_subquery():
    return (
        select(
            PriceModel.id.label("price_id"),
            func.row_number()
            .over(
                partition_by=(PriceModel.producto_fuente_id, PriceModel.sucursal_id),
                order_by=PriceModel.fecha_relevamiento.desc(),
            )
            .label("row_number"),
        )
        .subquery()
    )


@router.get("/catalog/products")
async def list_products(
    session: SessionDependency,
    q: str | None = Query(default=None, max_length=120),
    category_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    filters = [ProductModel.activo.is_(True)]
    if q and q.strip():
        filters.append(ProductModel.nombre_normalizado.ilike(f"%{q.strip()}%"))
    if category_id:
        filters.append(ProductModel.categoria_id == category_id)

    total = await session.scalar(select(func.count()).select_from(ProductModel).where(*filters)) or 0
    rows = await session.execute(
        select(ProductModel, BrandModel.nombre, ProductCategoryModel.nombre)
        .outerjoin(BrandModel, ProductModel.marca_id == BrandModel.id)
        .outerjoin(ProductCategoryModel, ProductModel.categoria_id == ProductCategoryModel.id)
        .where(*filters)
        .order_by(ProductModel.nombre_normalizado)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [
            {
                "id": str(product.id),
                "nombre": product.nombre_normalizado,
                "marca": brand_name,
                "categoria": category_name,
                "unidad_medida": product.unidad_medida,
                "contenido_neto": _decimal(product.contenido_neto),
                "codigo_interno": product.codigo_interno,
            }
            for product, brand_name, category_name in rows.all()
        ],
        "pagination": _pagination(page, page_size, total),
    }


@router.get("/catalog/categories")
async def list_categories(session: SessionDependency) -> dict:
    rows = await session.scalars(
        select(ProductCategoryModel)
        .where(ProductCategoryModel.activo.is_(True))
        .order_by(ProductCategoryModel.nombre)
    )
    return {"items": [{"id": str(category.id), "nombre": category.nombre} for category in rows.all()]}


@router.get("/locations/cities")
async def list_cities(session: SessionDependency) -> dict:
    rows = await session.execute(
        select(CityModel, ProvinceModel.nombre)
        .join(ProvinceModel, CityModel.provincia_id == ProvinceModel.id)
        .order_by(CityModel.nombre)
    )
    return {
        "items": [
            {
                "id": str(city.id),
                "nombre": city.nombre,
                "provincia": province_name,
                "latitud": float(city.latitud) if city.latitud is not None else None,
                "longitud": float(city.longitud) if city.longitud is not None else None,
            }
            for city, province_name in rows.all()
        ]
    }


@router.get("/supermarkets")
async def list_supermarkets(session: SessionDependency) -> dict:
    rows = await session.scalars(
        select(SupermarketModel)
        .where(SupermarketModel.activo.is_(True))
        .order_by(SupermarketModel.nombre)
    )
    return {"items": [{"id": str(item.id), "nombre": item.nombre} for item in rows.all()]}


@router.get("/branches")
async def list_branches(
    session: SessionDependency,
    city_id: UUID | None = None,
    supermarket_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    filters = [BranchModel.activo.is_(True)]
    if city_id:
        filters.append(BranchModel.ciudad_id == city_id)
    if supermarket_id:
        filters.append(BranchModel.supermercado_id == supermarket_id)

    total = await session.scalar(select(func.count()).select_from(BranchModel).where(*filters)) or 0
    rows = await session.execute(
        select(BranchModel, SupermarketModel.nombre, CityModel.nombre)
        .join(SupermarketModel, BranchModel.supermercado_id == SupermarketModel.id)
        .join(CityModel, BranchModel.ciudad_id == CityModel.id)
        .where(*filters)
        .order_by(SupermarketModel.nombre, BranchModel.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [
            _branch_payload(branch, supermarket_name, city_name)
            for branch, supermarket_name, city_name in rows.all()
        ],
        "pagination": _pagination(page, page_size, total),
    }


@router.get("/prices/current")
async def list_current_prices(
    session: SessionDependency,
    product_id: UUID | None = None,
    city_id: UUID | None = None,
    branch_id: UUID | None = None,
    supermarket_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    latest = _latest_prices_subquery()
    filters = [latest.c.row_number == 1]
    if product_id:
        filters.append(ProductModel.id == product_id)
    if city_id:
        filters.append(BranchModel.ciudad_id == city_id)
    if branch_id:
        filters.append(BranchModel.id == branch_id)
    if supermarket_id:
        filters.append(SupermarketModel.id == supermarket_id)

    statement = (
        select(
            PriceModel,
            ProductModel.nombre_normalizado,
            ProductSourceModel.nombre_original,
            BranchModel.nombre,
            BranchModel.direccion,
            SupermarketModel.nombre,
            CityModel.nombre,
        )
        .join(latest, latest.c.price_id == PriceModel.id)
        .join(ProductSourceModel, PriceModel.producto_fuente_id == ProductSourceModel.id)
        .join(ProductModel, ProductSourceModel.producto_id == ProductModel.id)
        .join(BranchModel, PriceModel.sucursal_id == BranchModel.id)
        .join(SupermarketModel, BranchModel.supermercado_id == SupermarketModel.id)
        .join(CityModel, BranchModel.ciudad_id == CityModel.id)
        .where(*filters)
        .order_by(ProductModel.nombre_normalizado, SupermarketModel.nombre, BranchModel.nombre)
    )
    total = await session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = await session.execute(statement.offset((page - 1) * page_size).limit(page_size))
    return {
        "items": [
            {
                "id": str(price.id),
                "producto": product_name,
                "producto_fuente": source_name,
                "sucursal": branch_name,
                "direccion": address,
                "supermercado": supermarket_name,
                "ciudad": city_name,
                "precio": _decimal(price.precio, 2),
                "moneda": price.moneda,
                "fecha_relevamiento": price.fecha_relevamiento.isoformat(),
                "disponible": price.disponible,
                "promocion": price.promocion,
            }
            for price, product_name, source_name, branch_name, address, supermarket_name, city_name in rows.all()
        ],
        "pagination": _pagination(page, page_size, total),
    }


@router.post("/decisions/ranking")
async def calculate_ranking(request: RankingRequest, session: SessionDependency) -> dict:
    city = await session.get(CityModel, request.city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudad no encontrada.")
    if city.latitud is None or city.longitud is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La ciudad no tiene coordenadas para calcular distancias.",
        )

    quantities = {item.product_id: item.quantity for item in request.items}
    product_rows = await session.execute(
        select(ProductModel.id, ProductModel.nombre_normalizado).where(
            ProductModel.id.in_(quantities), ProductModel.activo.is_(True)
        )
    )
    product_names = {product_id: name for product_id, name in product_rows.all()}
    if set(quantities) - set(product_names):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uno o mÃ¡s productos no existen.")

    branch_rows = await session.execute(
        select(BranchModel, SupermarketModel.nombre, CityModel.nombre)
        .join(SupermarketModel, BranchModel.supermercado_id == SupermarketModel.id)
        .join(CityModel, BranchModel.ciudad_id == CityModel.id)
        .where(BranchModel.activo.is_(True), SupermarketModel.activo.is_(True))
        .order_by(SupermarketModel.nombre, BranchModel.nombre)
    )
    branches = branch_rows.all()
    if not branches:
        return {"origen": {"id": str(city.id), "nombre": city.nombre}, "ranking": [], "incomplete": []}

    latest = _latest_prices_subquery()
    price_rows = await session.execute(
        select(PriceModel, ProductSourceModel.producto_id)
        .join(latest, latest.c.price_id == PriceModel.id)
        .join(ProductSourceModel, PriceModel.producto_fuente_id == ProductSourceModel.id)
        .where(
            latest.c.row_number == 1,
            PriceModel.disponible.is_(True),
            ProductSourceModel.producto_id.in_(quantities),
            PriceModel.sucursal_id.in_([branch.id for branch, _, _ in branches]),
        )
    )
    prices: dict[UUID, dict[UUID, PriceModel]] = defaultdict(dict)
    observed_at: datetime | None = None
    for price, product_id in price_rows.all():
        prices[price.sucursal_id][product_id] = price
        if observed_at is None or price.fecha_relevamiento > observed_at:
            observed_at = price.fecha_relevamiento

    distance_service = HaversineDistanceService()
    origin = GeoPoint(latitude=city.latitud, longitude=city.longitud)
    complete_candidates: list[tuple[BranchModel, str, str, Decimal, Decimal]] = []
    incomplete: list[dict] = []
    for branch, supermarket_name, branch_city_name in branches:
        branch_prices = prices[branch.id]
        missing_products = [
            {"id": str(product_id), "nombre": product_names[product_id]}
            for product_id in quantities
            if product_id not in branch_prices
        ]
        branch_data = _branch_payload(branch, supermarket_name, branch_city_name)
        if missing_products:
            incomplete.append({"sucursal": branch_data, "productos_faltantes": missing_products})
            continue
        total = sum(
            (branch_prices[product_id].precio * quantity for product_id, quantity in quantities.items()),
            Decimal("0"),
        )
        distance = distance_service.calculate(
            origin,
            GeoPoint(latitude=branch.latitud, longitude=branch.longitud),
        ).kilometers
        complete_candidates.append((branch, supermarket_name, branch_city_name, total, distance))

    maximum_total = max((candidate[3] for candidate in complete_candidates), default=Decimal("0"))
    alternatives = [
        Alternative(
            branch_id=branch.id,
            supermarket_name=supermarket_name,
            branch_name=branch.nombre,
            total_cost=total,
            distance_km=distance,
            saving=maximum_total - total,
        )
        for branch, supermarket_name, _, total, distance in complete_candidates
    ]
    weights = CriteriaWeights(
        price=request.weights.price,
        distance=request.weights.distance,
        saving=request.weights.saving,
    )
    ranking = WeightedSumModel().rank(alternatives, weights) if alternatives else []
    candidates_by_id = {
        branch.id: (branch, supermarket_name, city_name)
        for branch, supermarket_name, city_name, _, _ in complete_candidates
    }

    return {
        "origen": {"id": str(city.id), "nombre": city.nombre},
        "pesos": {
            "precio": _decimal(weights.price),
            "distancia": _decimal(weights.distance),
            "ahorro": _decimal(weights.saving),
        },
        "fecha_relevamiento": observed_at.isoformat() if observed_at else None,
        "ranking": [
            {
                "posicion": result.position,
                "sucursal": _branch_payload(*candidates_by_id[result.branch_id]),
                "total": _decimal(result.total_cost, 2),
                "distancia_km": _decimal(result.distance_km, 2),
                "ahorro": _decimal(result.saving, 2),
                "puntaje": _decimal(result.score, 4),
            }
            for result in ranking
        ],
        "incomplete": sorted(
            incomplete,
            key=lambda item: (len(item["productos_faltantes"]), item["sucursal"]["supermercado"]),
        ),
    }
