"""VTEX checkout session helpers for catalog sources that require a postal code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass(frozen=True)
class VtexLocationTarget:
    """Minimal address information required by VTEX to resolve a delivery region."""

    city: str
    postal_code: str
    state: str
    country: str = "ARG"


@dataclass(frozen=True)
class VtexRegionContext:
    """A confirmed VTEX checkout session context used by catalog requests."""

    target: VtexLocationTarget
    sales_channel: str


class VtexRegionContextError(RuntimeError):
    """Raised when VTEX cannot persist or confirm a requested delivery region."""


CARREFOUR_LOCATION_TARGETS = {
    "comodoro rivadavia": VtexLocationTarget(
        city="Comodoro Rivadavia",
        postal_code="9000",
        state="CH",
    ),
}

CHANGOMAS_LOCATION_TARGETS = {
    "comodoro rivadavia": VtexLocationTarget(
        city="Comodoro Rivadavia",
        postal_code="9000",
        state="CH",
    ),
}


def get_carrefour_location_target(city: str) -> VtexLocationTarget:
    """Returns Carrefour's supported postal-code target for a configured pilot city."""
    target = CARREFOUR_LOCATION_TARGETS.get(city.strip().casefold())
    if target is None:
        raise LookupError(f"Carrefour has no configured VTEX location target for {city!r}.")
    return target


def get_changomas_location_target(city: str) -> VtexLocationTarget:
    """Returns Mas Online's supported delivery target for the configured pilot city."""
    target = CHANGOMAS_LOCATION_TARGETS.get(city.strip().casefold())
    if target is None:
        raise LookupError(f"Chango Mas has no configured VTEX location target for {city!r}.")
    return target


def build_shipping_data_payload(target: VtexLocationTarget) -> dict[str, Any]:
    """Builds the public checkout attachment accepted by VTEX for a postal code."""
    address = {
        "addressType": "residential",
        "receiverName": "",
        "country": target.country,
        "postalCode": target.postal_code,
        "city": target.city,
        "state": target.state,
        "street": "",
        "number": "",
        "neighborhood": "",
        "complement": "",
        "reference": "",
        "geoCoordinates": [],
    }
    return {
        "selectedAddresses": [address],
        "clearAddressIfPostalCodeNotFound": False,
    }


async def resolve_vtex_region_context(
    session: aiohttp.ClientSession,
    *,
    base_url: str,
    target: VtexLocationTarget,
    sales_channel: str = "1",
    source_name: str,
) -> VtexRegionContext:
    """Sets the VTEX checkout address and verifies the returned postal-code context."""
    order_form = await _get_json(session, f"{base_url.rstrip('/')}/api/checkout/pub/orderForm")
    order_form_id = order_form.get("orderFormId") if isinstance(order_form, dict) else None
    if not isinstance(order_form_id, str) or not order_form_id.strip():
        raise VtexRegionContextError(f"{source_name} did not provide a valid VTEX order form.")

    shipping_data = await _post_json(
        session,
        f"{base_url.rstrip('/')}/api/checkout/pub/orderForm/{order_form_id}/attachments/shippingData",
        build_shipping_data_payload(target),
    )
    if not _is_confirmed_target(shipping_data, target):
        raise VtexRegionContextError(
            f"{source_name} did not confirm postal code {target.postal_code!r}."
        )
    resolved_channel = order_form.get("salesChannel", sales_channel)
    return VtexRegionContext(target=target, sales_channel=str(resolved_channel))


async def _get_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url) as response:
        if response.status >= 400:
            raise VtexRegionContextError(f"VTEX order form request returned HTTP {response.status}.")
        return await response.json(content_type=None)


async def _post_json(session: aiohttp.ClientSession, url: str, payload: dict[str, Any]) -> Any:
    async with session.post(url, json=payload) as response:
        if response.status >= 400:
            raise VtexRegionContextError(f"VTEX shipping data request returned HTTP {response.status}.")
        return await response.json(content_type=None)


def _is_confirmed_target(payload: Any, target: VtexLocationTarget) -> bool:
    if not isinstance(payload, dict):
        return False
    shipping_data = payload.get("shippingData", payload)
    if not isinstance(shipping_data, dict):
        return False
    address = shipping_data.get("address")
    if not isinstance(address, dict):
        return False
    return (
        str(address.get("postalCode") or "").strip() == target.postal_code
        and str(address.get("country") or "").strip().upper() == target.country
    )
