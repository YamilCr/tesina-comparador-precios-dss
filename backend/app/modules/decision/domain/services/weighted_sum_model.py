"""Servicio de dominio que implementa el modelo de suma ponderada."""

from decimal import Decimal

from ..entities.alternative import Alternative
from ..entities.ranking_result import RankingResult
from ..value_objects.criteria_weights import CriteriaWeights
from .criteria_normalizer import CriteriaNormalizer


class WeightedSumModel:
    """Calcula un ranking de alternativas a partir de criterios normalizados."""

    def __init__(self, normalizer: CriteriaNormalizer | None = None) -> None:
        """Permite utilizar un normalizador específico o el normalizador por defecto."""
        self._normalizer = normalizer or CriteriaNormalizer()

    def rank(
        self,
        alternatives: list[Alternative],
        weights: CriteriaWeights,
    ) -> list[RankingResult]:
        """Ordena alternativas usando precio, distancia y ahorro normalizados."""
        if not alternatives:
            raise ValueError("At least one alternative is required for ranking.")

        price_scores = self._normalizer.normalize_cost_values(
            [alternative.total_cost for alternative in alternatives]
        )
        distance_scores = self._normalizer.normalize_cost_values(
            [alternative.distance_km for alternative in alternatives]
        )
        saving_scores = self._normalizer.normalize_benefit_values(
            [alternative.saving for alternative in alternatives]
        )

        scored_alternatives: list[tuple[Alternative, Decimal]] = []
        for alternative, price_score, distance_score, saving_score in zip(
            alternatives,
            price_scores,
            distance_scores,
            saving_scores,
            strict=True,
        ):
            score = (
                weights.price * price_score
                + weights.distance * distance_score
                + weights.saving * saving_score
            )
            scored_alternatives.append((alternative, score))

        scored_alternatives.sort(key=lambda item: item[1], reverse=True)
        return [
            RankingResult(
                position=position,
                branch_id=alternative.branch_id,
                supermarket_name=alternative.supermarket_name,
                branch_name=alternative.branch_name,
                total_cost=alternative.total_cost,
                distance_km=alternative.distance_km,
                saving=alternative.saving,
                score=score,
                missing_products_count=alternative.missing_products_count,
            )
            for position, (alternative, score) in enumerate(scored_alternatives, start=1)
        ]
