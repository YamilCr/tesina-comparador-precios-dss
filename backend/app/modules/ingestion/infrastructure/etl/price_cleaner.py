"""Validation and normalization helpers for extracted prices."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MAX_PRICE = Decimal("10000000")


def clean_price(value: Decimal | None) -> Decimal:
    """Returns a valid ARS amount rounded to cents or raises ``ValueError``."""
    if value is None:
        raise ValueError("Missing price.")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Invalid price.") from error
    if not amount.is_finite() or amount <= Decimal("0"):
        raise ValueError("Price must be greater than zero.")
    if amount > MAX_PRICE:
        raise ValueError("Price exceeds the quality limit.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
