"""Rutas HTTP para calcular recomendaciones DSS."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_unit_of_work
from app.modules.basket.application.dto import BasketItemInputDTO
from app.modules.decision.application.dto import RankingRequestDTO
from app.modules.decision.application.use_cases import GenerateRankingUseCase
from app.modules.decision.domain.value_objects import CriteriaWeights
from app.shared.application import UnitOfWorkPort

from .schemas import RankingRequest


router = APIRouter(prefix="/decisions", tags=["decision"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


async def _resolve_origin(
    uow: UnitOfWorkPort,
    request: RankingRequest,
) -> tuple[Decimal, Decimal]:
    """Resuelve el punto de origen desde coordenadas directas o ciudad."""
    if request.origin_latitude is not None and request.origin_longitude is not None:
        return request.origin_latitude, request.origin_longitude

    if request.city_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Debe enviar coordenadas de origen o city_id.",
        )

    async with uow:
        city = await uow.cities.get_by_id(request.city_id)

    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudad no encontrada.")
    if city.latitude is None or city.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La ciudad no tiene coordenadas para calcular distancias.",
        )
    return city.latitude, city.longitude


def _ranking_payload(response) -> dict:
    """Convierte la respuesta de aplicación en JSON estable para HTTP."""
    return {
        "count": len(response.ranking),
        "incomplete_count": len(response.incomplete_branches),
        "weights": {
            "price": str(response.weights.price),
            "distance": str(response.weights.distance),
            "saving": str(response.weights.saving),
        },
        "observed_at": response.observed_at.isoformat() if response.observed_at else None,
        "ranking": [
            {
                "position": result.position,
                "branch": {
                    "id": str(result.branch.id),
                    "supermarket_id": str(result.branch.supermarket_id),
                    "supermarket_name": result.branch.supermarket_name,
                    "city_id": str(result.branch.city_id),
                    "name": result.branch.name,
                    "address": result.branch.address,
                    "latitude": str(result.branch.latitude),
                    "longitude": str(result.branch.longitude),
                },
                "total_cost": str(result.total_cost),
                "distance_km": str(result.distance_km),
                "saving": str(result.saving),
                "score": str(result.score),
                "missing_products_count": result.missing_products_count,
            }
            for result in response.ranking
        ],
        "incomplete_branches": [
            {
                "branch": {
                    "id": str(item.branch.id),
                    "supermarket_id": str(item.branch.supermarket_id),
                    "supermarket_name": item.branch.supermarket_name,
                    "city_id": str(item.branch.city_id),
                    "name": item.branch.name,
                    "address": item.branch.address,
                    "latitude": str(item.branch.latitude),
                    "longitude": str(item.branch.longitude),
                },
                "missing_products": [
                    {"id": str(product.id), "normalized_name": product.normalized_name}
                    for product in item.missing_products
                ],
            }
            for item in response.incomplete_branches
        ],
    }


@router.post("/ranking")
async def calculate_ranking(request: RankingRequest, uow: UnitOfWorkDependency) -> dict:
    """Calcula un ranking multicriterio para una canasta temporal."""
    origin_latitude, origin_longitude = await _resolve_origin(uow, request)
    try:
        response = await GenerateRankingUseCase(uow).execute(
            RankingRequestDTO(
                items=[
                    BasketItemInputDTO(
                        product_id=item.product_id,
                        quantity=item.quantity,
                    )
                    for item in request.items
                ],
                origin_latitude=origin_latitude,
                origin_longitude=origin_longitude,
                branch_ids=request.branch_ids,
                weights=CriteriaWeights(
                    price=request.weights.price,
                    distance=request.weights.distance,
                    saving=request.weights.saving,
                ),
            )
        )
    except ValueError as error:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(error).startswith("Products not found")
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return _ranking_payload(response)
