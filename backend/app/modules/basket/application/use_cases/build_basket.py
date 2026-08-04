"""Caso de uso para construir una canasta temporal no persistida."""

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from app.modules.basket.application.dto.basket_dto import (
    BasketDTO,
    BasketItemDTO,
    BasketItemInputDTO,
)
from app.modules.basket.domain.entities import Basket, BasketItem


def basket_to_dto(basket: Basket) -> BasketDTO:
    """Convierte una entidad Basket en un DTO de aplicación."""
    return BasketDTO(
        items=[
            BasketItemDTO(product_id=item.product_id, quantity=item.quantity)
            for item in basket.items
        ],
        total_items=basket.total_items(),
        product_ids=basket.product_ids(),
    )


class BuildBasketUseCase:
    """Valida y consolida una canasta anónima en memoria."""

    def execute(self, items: list[BasketItemInputDTO]) -> Basket:
        """Construye una entidad Basket, sumando cantidades repetidas por producto."""
        if not items:
            raise ValueError("Basket requires at least one item.")

        quantities_by_product: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in items:
            quantities_by_product[item.product_id] += item.quantity

        basket_items = [
            BasketItem(product_id=product_id, quantity=quantity)
            for product_id, quantity in quantities_by_product.items()
        ]
        return Basket(items=basket_items)
