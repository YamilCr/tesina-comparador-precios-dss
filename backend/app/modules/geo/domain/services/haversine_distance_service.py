"""Servicio de dominio para calcular distancias geográficas aproximadas."""

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from ..value_objects.distance import Distance
from ..value_objects.geo_point import GeoPoint


class HaversineDistanceService:
    """Calcula la distancia entre dos puntos mediante la fórmula de Haversine."""

    _EARTH_RADIUS_KM = 6371.0088

    def calculate(self, origin: GeoPoint, destination: GeoPoint) -> Distance:
        """Calcula la distancia aproximada entre origen y destino en kilómetros."""
        latitude_delta = radians(float(destination.latitude - origin.latitude))
        longitude_delta = radians(float(destination.longitude - origin.longitude))
        origin_latitude = radians(float(origin.latitude))
        destination_latitude = radians(float(destination.latitude))

        haversine_value = (
            sin(latitude_delta / 2) ** 2
            + cos(origin_latitude) * cos(destination_latitude) * sin(longitude_delta / 2) ** 2
        )
        central_angle = 2 * asin(sqrt(haversine_value))
        return Distance(kilometers=Decimal(str(self._EARTH_RADIUS_KM * central_angle)))
