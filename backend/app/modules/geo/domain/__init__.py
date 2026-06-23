"""Reglas y modelos puros del dominio geográfico, sin almacenar ubicaciones."""

from .services import HaversineDistanceService
from .value_objects import Distance, GeoPoint

__all__ = ["Distance", "GeoPoint", "HaversineDistanceService"]
