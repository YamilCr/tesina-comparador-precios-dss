"""Servicio de dominio para normalizar criterios de costo y beneficio."""

from decimal import Decimal


class CriteriaNormalizer:
    """Convierte valores de criterios en puntajes normalizados entre cero y uno."""

    @staticmethod
    def normalize_cost_values(values: list[Decimal]) -> list[Decimal]:
        """Normaliza costos: el menor valor recibe el mayor puntaje."""
        if not values:
            return []

        minimum = min(values)
        maximum = max(values)
        if minimum == maximum:
            return [Decimal("1") for _ in values]

        value_range = maximum - minimum
        return [(maximum - value) / value_range for value in values]

    @staticmethod
    def normalize_benefit_values(values: list[Decimal]) -> list[Decimal]:
        """Normaliza beneficios: el mayor valor recibe el mayor puntaje."""
        if not values:
            return []

        minimum = min(values)
        maximum = max(values)
        if minimum == maximum:
            return [Decimal("1") for _ in values]

        value_range = maximum - minimum
        return [(value - minimum) / value_range for value in values]
