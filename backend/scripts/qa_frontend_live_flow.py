"""Exercises the live frontend flow in a real Chromium browser."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


FRONTEND_URL = "http://127.0.0.1:5173/comparar"
TARGET_SOURCES = {"Carrefour", "La Coope", "La Anónima"}


async def main() -> None:
    artifact_dir = Path(__file__).resolve().parents[2] / "output" / "playwright"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifact_dir / "frontend-live-search-prices-ranking.png"
    mobile_screenshot_path = artifact_dir / "frontend-live-search-prices-ranking-mobile.png"
    network: list[dict[str, str | int]] = []
    console_errors: list[str] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "response",
            lambda response: network.append(
                {
                    "method": response.request.method,
                    "status": response.status,
                    "url": response.url,
                }
            )
            if "/api/" in response.url
            else None,
        )
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )

        await page.goto(FRONTEND_URL, wait_until="networkidle")
        city_option = page.locator("#city option", has_text="Comodoro Rivadavia").first
        city_id = await city_option.get_attribute("value")
        if city_id is None:
            raise RuntimeError("Comodoro Rivadavia is not available in the city selector.")
        await page.locator("#city").select_option(city_id)
        await page.get_by_placeholder("Buscar producto").fill("coca cola")

        source_labels = page.locator('label:has(input[type="checkbox"])')
        selected_sources: list[str] = []
        for index in range(await source_labels.count()):
            label = source_labels.nth(index)
            name = (await label.inner_text()).strip()
            checkbox = label.locator('input[type="checkbox"]')
            if name in TARGET_SOURCES:
                await checkbox.check()
                selected_sources.append(name)
            else:
                await checkbox.uncheck()

        await page.get_by_role("button", name="Actualizar precios").click()
        await page.get_by_text(re.compile(r"\d+ precios cargados")).wait_for(timeout=120_000)
        refresh_summary = await page.get_by_text(re.compile(r"\d+ precios cargados")).inner_text()

        add_button = page.get_by_role(
            "button",
            name=re.compile(r"Agregar Gaseosa Cola Pet Coca Cola x 2,5 Lt\.", re.I),
        )
        if not await add_button.count():
            add_button = page.get_by_role("button", name=re.compile(r"Agregar .*Coca.*Cola", re.I)).first
        await add_button.first.click()

        prices_section = page.get_by_role("heading", name="Precios vigentes").locator("..")
        await prices_section.get_by_text(re.compile(r"\d+ precios para la canasta")).wait_for(
            timeout=30_000
        )
        price_rows = page.locator("table tbody tr")
        await price_rows.first.wait_for(timeout=30_000)
        price_row_count = await price_rows.count()

        await page.get_by_role("button", name="Calcular ranking").click()
        await page.get_by_role("heading", name="Ranking de alternativas").wait_for(timeout=30_000)
        ranking_count = await page.get_by_text(re.compile(r"\d+ alternativas completas")).inner_text()
        ranking_observed_at = await page.get_by_text(re.compile(r"^Calculado desde")).inner_text()

        await page.screenshot(path=screenshot_path, full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(300)
        horizontal_overflow = await page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        await page.screenshot(path=mobile_screenshot_path, full_page=True)
        await browser.close()

    relevant_network = [
        entry
        for entry in network
        if any(
            segment in str(entry["url"])
            for segment in ("refresh-concurrently", "/prices/current", "/decisions/ranking")
        )
    ]
    failed_requests = [entry for entry in relevant_network if int(entry["status"]) >= 400]
    result = {
        "frontend_url": FRONTEND_URL,
        "selected_sources": selected_sources,
        "refresh_summary": refresh_summary,
        "price_rows": price_row_count,
        "ranking_summary": ranking_count,
        "ranking_observed_at": ranking_observed_at,
        "network": relevant_network,
        "failed_requests": failed_requests,
        "console_errors": console_errors,
        "mobile_horizontal_overflow": horizontal_overflow,
        "screenshot": str(screenshot_path),
        "mobile_screenshot": str(mobile_screenshot_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
