from decimal import Decimal
from uuid import uuid4

from app.modules.decision.domain.entities import Alternative
from app.modules.decision.domain.services import WeightedSumModel
from app.modules.decision.domain.value_objects import CriteriaWeights


def test_weighted_sum_prefers_the_lower_cost_when_price_has_full_weight() -> None:
    alternatives = [
        Alternative(uuid4(), "A", "Centro", Decimal("120"), Decimal("1"), Decimal("0")),
        Alternative(uuid4(), "B", "Norte", Decimal("100"), Decimal("5"), Decimal("20")),
    ]

    ranking = WeightedSumModel().rank(
        alternatives,
        CriteriaWeights(price=Decimal("1"), distance=Decimal("0"), saving=Decimal("0")),
    )

    assert ranking[0].supermarket_name == "B"
    assert ranking[0].position == 1
