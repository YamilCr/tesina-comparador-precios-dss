"""Integration tests for ingestion source administration and run lifecycle."""

from collections.abc import Callable
from typing import Any

import pytest

from .conftest import ASGIResponse, IntegrationSeedData


@pytest.mark.asyncio
async def test_ingestion_administration_tracks_source_and_run_lifecycle(
    sqlite_uow_override: None,
    asgi_request: Callable[..., Any],
    seed_data: IntegrationSeedData,
) -> None:
    """Creates a source and records successful and failed audit runs."""
    create_response: ASGIResponse = await asgi_request(
        "POST",
        "/api/v1/ingestion/sources",
        json_body={
            "supermarket_id": str(seed_data.la_anonima_id),
            "name": "La Anonima catalog",
            "base_url": "https://example.test/la-anonima",
        },
    )
    assert create_response.status_code == 201
    source = create_response.json()
    source_id = source["id"]
    assert source["active"] is True

    sources_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/ingestion/sources",
        query={"active_only": "true"},
    )
    assert sources_response.status_code == 200
    assert sources_response.json()["count"] == 1

    running_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/sources/{source_id}/runs",
    )
    assert running_response.status_code == 201
    running_run = running_response.json()
    assert running_run["status"] == "running"

    duplicate_run_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/sources/{source_id}/runs",
    )
    assert duplicate_run_response.status_code == 409

    successful_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/runs/{running_run['id']}/succeed",
        json_body={"items_scraped": 25, "items_loaded": 20},
    )
    assert successful_response.status_code == 200
    assert successful_response.json()["status"] == "succeeded"
    assert successful_response.json()["items_loaded"] == 20

    failed_run_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/sources/{source_id}/runs",
    )
    failed_run = failed_run_response.json()
    failed_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/runs/{failed_run['id']}/fail",
        json_body={"error_message": "Source returned an invalid response."},
    )
    assert failed_response.status_code == 200
    assert failed_response.json()["status"] == "failed"

    runs_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/ingestion/runs",
        query={"source_id": source_id},
    )
    assert runs_response.status_code == 200
    assert runs_response.json()["count"] == 2
    assert {run["status"] for run in runs_response.json()["items"]} == {"succeeded", "failed"}

    deactivate_response: ASGIResponse = await asgi_request(
        "PATCH",
        f"/api/v1/ingestion/sources/{source_id}",
        json_body={"active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["active"] is False

    inactive_start_response: ASGIResponse = await asgi_request(
        "POST",
        f"/api/v1/ingestion/sources/{source_id}/runs",
    )
    assert inactive_start_response.status_code == 422
