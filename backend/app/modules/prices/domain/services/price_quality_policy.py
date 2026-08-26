"""Política explicable de calidad para precios actuales."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median
from typing import Literal
from uuid import UUID

from app.modules.prices.domain.entities import Price


PriceQualityStatus = Literal["fresh", "stale", "suspect"]


@dataclass(frozen=True)
class PriceQualityAssessment:
    """Resultado auditable de evaluar un precio actual."""

    price: Price
    status: PriceQualityStatus
    reason: str | None
    age_days: int


@dataclass(frozen=True)
class PriceQualitySelection:
    """Precios actuales separados según su aptitud para decisiones."""

    assessments: list[PriceQualityAssessment]

    @property
    def eligible(self) -> list[Price]:
        """Devuelve precios vigentes y no anómalos."""
        return [item.price for item in self.assessments if item.status == "fresh"]

    @property
    def stale(self) -> list[Price]:
        """Devuelve precios excluidos por antigüedad."""
        return [item.price for item in self.assessments if item.status == "stale"]

    @property
    def suspect(self) -> list[Price]:
        """Devuelve precios excluidos por desvío histórico extremo."""
        return [item.price for item in self.assessments if item.status == "suspect"]

    def assessment_by_id(self) -> dict[UUID, PriceQualityAssessment]:
        """Indexa evaluaciones por identificador de precio."""
        return {item.price.id: item for item in self.assessments}


class PriceQualityPolicy:
    """Evalúa vigencia y anomalías sin modificar el historial persistido."""

    def __init__(
        self,
        *,
        max_age_days: int | None = 14,
        minimum_history: int = 2,
        lower_median_ratio: Decimal = Decimal("0.4"),
        upper_median_ratio: Decimal = Decimal("2.5"),
    ) -> None:
        if max_age_days is not None and max_age_days <= 0:
            raise ValueError("Maximum price age must be greater than zero.")
        if minimum_history < 1:
            raise ValueError("Minimum price history must be at least one.")
        if lower_median_ratio <= 0 or upper_median_ratio <= lower_median_ratio:
            raise ValueError("Price anomaly ratios are invalid.")
        self._max_age_days = max_age_days
        self._minimum_history = minimum_history
        self._lower_median_ratio = lower_median_ratio
        self._upper_median_ratio = upper_median_ratio

    def evaluate(self, prices: list[Price], *, as_of: datetime) -> PriceQualitySelection:
        """Evalúa el último precio disponible de cada publicación y sucursal."""
        evaluation_time = self._as_utc(as_of)
        latest = self._select_latest(prices)
        history_by_key = self._history_by_key(prices)
        assessments: list[PriceQualityAssessment] = []

        for price in latest:
            age_days = self._age_days(price.observed_at, evaluation_time)
            if self._max_age_days is not None and age_days > self._max_age_days:
                assessments.append(
                    PriceQualityAssessment(
                        price=price,
                        status="stale",
                        reason=f"older_than_{self._max_age_days}_days",
                        age_days=age_days,
                    )
                )
                continue

            history = [
                item.amount
                for item in history_by_key[self._key(price)]
                if item.available
                and item.amount > 0
                and self._as_utc(item.observed_at) < self._as_utc(price.observed_at)
            ]
            if not price.promotion and self._is_suspect(price.amount, history):
                assessments.append(
                    PriceQualityAssessment(
                        price=price,
                        status="suspect",
                        reason="outside_historical_median_range",
                        age_days=age_days,
                    )
                )
                continue

            assessments.append(
                PriceQualityAssessment(
                    price=price,
                    status="fresh",
                    reason=None,
                    age_days=age_days,
                )
            )

        return PriceQualitySelection(assessments=assessments)

    def _is_suspect(self, amount: Decimal, history: list[Decimal]) -> bool:
        if len(history) < self._minimum_history:
            return False
        historical_median = Decimal(str(median(history)))
        if historical_median <= 0:
            return False
        ratio = amount / historical_median
        return ratio < self._lower_median_ratio or ratio > self._upper_median_ratio

    @classmethod
    def _select_latest(cls, prices: list[Price]) -> list[Price]:
        latest: dict[tuple[UUID, UUID], Price] = {}
        for price in prices:
            if not price.available:
                continue
            key = cls._key(price)
            current = latest.get(key)
            if current is None or cls._is_newer(price, current):
                latest[key] = price
        return sorted(
            latest.values(),
            key=lambda item: (
                cls._as_utc(item.observed_at),
                str(item.branch_id),
                str(item.product_source_id),
            ),
            reverse=True,
        )

    @classmethod
    def _history_by_key(cls, prices: list[Price]) -> dict[tuple[UUID, UUID], list[Price]]:
        grouped: dict[tuple[UUID, UUID], list[Price]] = {}
        for price in prices:
            grouped.setdefault(cls._key(price), []).append(price)
        return grouped

    @staticmethod
    def _key(price: Price) -> tuple[UUID, UUID]:
        return price.product_source_id, price.branch_id

    @classmethod
    def _is_newer(cls, candidate: Price, current: Price) -> bool:
        candidate_time = cls._as_utc(candidate.observed_at)
        current_time = cls._as_utc(current.observed_at)
        return candidate_time > current_time or (
            candidate_time == current_time and candidate.amount < current.amount
        )

    @classmethod
    def _age_days(cls, observed_at: datetime, as_of: datetime) -> int:
        elapsed = as_of - cls._as_utc(observed_at)
        return max(0, int(elapsed.total_seconds() // 86_400))

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
