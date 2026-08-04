"""Rutas HTTP para validar canastas temporales no persistidas."""

from fastapi import APIRouter, HTTPException, status

from app.modules.basket.application.dto import BasketItemInputDTO
from app.modules.basket.application.use_cases import BuildBasketUseCase, basket_to_dto
from app.shared.interfaces.http import collection_response

from .schemas import BasketRequest


router = APIRouter(prefix="/basket", tags=["basket"])


@router.post("/validate")
async def validate_basket(request: BasketRequest) -> dict:
    """Valida y consolida una canasta temporal sin persistirla."""
    try:
        basket = BuildBasketUseCase().execute(
            [
                BasketItemInputDTO(
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                for item in request.items
            ]
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    basket_dto = basket_to_dto(basket)
    response = collection_response(
        [
            {"product_id": str(item.product_id), "quantity": str(item.quantity)}
            for item in basket_dto.items
        ]
    )
    response["total_items"] = basket_dto.total_items
    response["product_ids"] = [str(product_id) for product_id in basket_dto.product_ids]
    return response
