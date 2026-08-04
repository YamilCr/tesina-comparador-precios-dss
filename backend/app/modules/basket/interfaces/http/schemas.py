"""Schemas HTTP para canastas temporales anónimas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BasketLineRequest(BaseModel):
    """Producto y cantidad recibidos por HTTP."""

    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class BasketRequest(BaseModel):
    """Solicitud para validar una canasta temporal."""

    items: list[BasketLineRequest] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "BasketRequest":
        """Evita productos duplicados en la entrada HTTP."""
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada producto debe aparecer una sola vez en la canasta.")
        return self
