"""Pruebas de integración livianas para el registro de rutas HTTP v1."""

from app.main import app


def test_api_v1_routes_are_registered() -> None:
    """Verifica que los endpoints iniciales estén publicados en OpenAPI."""
    paths = set(app.openapi()["paths"])

    assert "/health" in paths
    assert "/api/v1/catalog/products" in paths
    assert "/api/v1/catalog/categories" in paths
    assert "/api/v1/catalog/brands" in paths
    assert "/api/v1/locations/cities" in paths
    assert "/api/v1/supermarkets" in paths
    assert "/api/v1/branches" in paths
    assert "/api/v1/prices/current" in paths
    assert "/api/v1/prices/history" in paths
    assert "/api/v1/prices/compare" in paths
    assert "/api/v1/basket/validate" in paths
    assert "/api/v1/decisions/ranking" in paths
    assert "/api/v1/ingestion/sources" in paths
    assert "/api/v1/ingestion/sources/{source_id}" in paths
    assert "/api/v1/ingestion/sources/{source_id}/runs" in paths
    assert "/api/v1/ingestion/runs" in paths
    assert "/api/v1/ingestion/runs/{run_id}/succeed" in paths
    assert "/api/v1/ingestion/runs/{run_id}/fail" in paths
