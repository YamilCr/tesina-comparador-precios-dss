"""Pruebas de la política de calidad aplicada a precios actuales."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.modules.prices.domain.entities import Price
from app.modules.prices.domain.services import PriceQualityPolicy


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
BRANCH_ID = UUID("10000000-0000-0000-0000-000000000001")


def _price(
    suffix: int,
    *,
    source_suffix: int,
    amount: str,
    age_days: int,
    promotion: bool = False,
) -> Price:
    return Price(
        id=UUID(f"20000000-0000-0000-0000-{suffix:012d}"),
        product_source_id=UUID(
            f"30000000-0000-0000-0000-{source_suffix:012d}"
        ),
        branch_id=BRANCH_ID,
        amount=Decimal(amount),
        observed_at=NOW - timedelta(days=age_days),
        promotion=promotion,
    )


def test_quality_policy_separates_fresh_stale_and_suspect_prices() -> None:
    """Clasifica solo el último valor por fuente usando historial suficiente."""
    prices = [
        _price(1, source_suffix=1, amount="100", age_days=10),
        _price(2, source_suffix=1, amount="110", age_days=5),
        _price(3, source_suffix=1, amount="1000", age_days=0),
        _price(4, source_suffix=2, amount="250", age_days=20),
        _price(5, source_suffix=3, amount="300", age_days=1),
    ]

    result = PriceQualityPolicy(max_age_days=14).evaluate(prices, as_of=NOW)

    assert [price.id for price in result.eligible] == [prices[4].id]
    assert [price.id for price in result.stale] == [prices[3].id]
    assert [price.id for price in result.suspect] == [prices[2].id]
    assessments = result.assessment_by_id()
    assert assessments[prices[3].id].reason == "older_than_14_days"
    assert assessments[prices[2].id].reason == "outside_historical_median_range"


def test_quality_policy_does_not_flag_promotions_as_anomalies() -> None:
    """Una promoción explícita conserva aptitud aun con una caída extrema."""
    prices = [
        _price(6, source_suffix=4, amount="1000", age_days=10),
        _price(7, source_suffix=4, amount="1100", age_days=5),
        _price(8, source_suffix=4, amount="100", age_days=0, promotion=True),
    ]

    result = PriceQualityPolicy(max_age_days=14).evaluate(prices, as_of=NOW)

    assert [price.id for price in result.eligible] == [prices[2].id]
    assert result.suspect == []
