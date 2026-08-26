"""Rutas HTTP de precios conectadas con casos de uso de aplicación."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_unit_of_work
from app.modules.prices.application.commands import (
    CompareProductPricesQuery,
    CurrentPriceQuery,
    GetPriceHistoryQuery,
)
from app.modules.prices.application.dto import PriceDTO
from app.modules.prices.application.use_cases import (
    CompareProductPricesUseCase,
    GetPriceHistoryUseCase,
    ListCurrentPricesUseCase,
)
from app.shared.application import UnitOfWorkPort
from app.shared.interfaces.http import collection_response

from .schemas import PriceResponse


router = APIRouter(prefix="/prices", tags=["prices"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


async def _price_payloads(uow: UnitOfWorkPort, prices: list[PriceDTO]) -> list[dict]:
    """Convierte precios en respuestas enriquecidas para clientes HTTP."""
    if not prices:
        return []

    payloads: list[dict] = []
    async with uow as read_uow:
        for price in prices:
            product_id = None
            product_name = None
            product_source_name = None
            branch_name = None
            branch_address = None
            supermarket_id = None
            supermarket_name = None
            city_id = None
            city_name = None

            product_source = await read_uow.product_sources.get_by_id(price.product_source_id)
            if product_source is not None:
                product_id = product_source.product_id
                product_source_name = product_source.original_name
                product = await read_uow.products.get_by_id(product_source.product_id)
                if product is not None:
                    product_name = product.normalized_name

            branch = await read_uow.branches.get_by_id(price.branch_id)
            if branch is not None:
                branch_name = branch.name
                branch_address = branch.address
                supermarket_id = branch.supermarket_id
                city_id = branch.city_id
                supermarket = await read_uow.supermarkets.get_by_id(branch.supermarket_id)
                if supermarket is not None:
                    supermarket_name = supermarket.name
                city = await read_uow.cities.get_by_id(branch.city_id)
                if city is not None:
                    city_name = city.name

            payloads.append(
                PriceResponse(
                    id=price.id,
                    product_source_id=price.product_source_id,
                    product_id=product_id,
                    product_name=product_name,
                    product_source_name=product_source_name,
                    branch_id=price.branch_id,
                    branch_name=branch_name,
                    branch_address=branch_address,
                    supermarket_id=supermarket_id,
                    supermarket_name=supermarket_name,
                    city_id=city_id,
                    city_name=city_name,
                    amount=price.amount,
                    currency=price.currency,
                    observed_at=price.observed_at,
                    available=price.available,
                    promotion=price.promotion,
                    quality_status=price.quality_status,
                    quality_reason=price.quality_reason,
                    age_days=price.age_days,
                ).model_dump(mode="json")
            )
    return payloads


@router.get("/current")
async def list_current_prices(
    uow: UnitOfWorkDependency,
    product_id: UUID | None = None,
    product_source_id: UUID | None = None,
    branch_id: UUID | None = None,
    city_id: UUID | None = None,
    supermarket_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    as_of: datetime | None = None,
    max_age_days: int = Query(default=14, ge=1, le=90),
) -> dict:
    """Consulta precios actuales usando filtros definidos en application."""
    product_ids = [product_id] if product_id is not None else None
    try:
        selection = await ListCurrentPricesUseCase(uow).execute_with_quality(
            CurrentPriceQuery(
                product_ids=product_ids,
                product_source_id=product_source_id,
                branch_id=branch_id,
                city_id=city_id,
                supermarket_id=supermarket_id,
                limit=limit,
                as_of=as_of,
                max_age_days=max_age_days,
            )
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    response = collection_response(await _price_payloads(uow, selection.prices))
    response["quality"] = {
        "evaluated_at": selection.evaluated_at.isoformat(),
        "max_age_days": selection.max_age_days,
        "eligible_count": selection.eligible_count,
        "stale_excluded_count": selection.stale_excluded_count,
        "suspect_excluded_count": selection.suspect_excluded_count,
    }
    return response


@router.get("/history")
async def get_price_history(
    uow: UnitOfWorkDependency,
    product_source_id: UUID,
    branch_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """Consulta el historial de precios de un producto fuente."""
    prices = await GetPriceHistoryUseCase(uow).execute(
        GetPriceHistoryQuery(product_source_id=product_source_id, branch_id=branch_id)
    )
    prices = sorted(prices, key=lambda price: price.observed_at, reverse=True)[:limit]
    return collection_response(await _price_payloads(uow, prices))


@router.get("/compare")
async def compare_product_prices(
    uow: UnitOfWorkDependency,
    product_ids: list[UUID] = Query(...),
    branch_id: UUID | None = None,
    city_id: UUID | None = None,
    supermarket_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    as_of: datetime | None = None,
    max_age_days: int = Query(default=14, ge=1, le=90),
) -> dict:
    """Compara precios actuales para uno o más productos normalizados."""
    try:
        prices = await CompareProductPricesUseCase(uow).execute(
            CompareProductPricesQuery(
                product_ids=product_ids,
                branch_id=branch_id,
                city_id=city_id,
                supermarket_id=supermarket_id,
                limit=limit,
                as_of=as_of,
                max_age_days=max_age_days,
            )
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return collection_response(await _price_payloads(uow, prices))
