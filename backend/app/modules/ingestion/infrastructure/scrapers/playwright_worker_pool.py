"""Reusable bounded browser pool for JavaScript-rendered supermarket sources."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright


Result = TypeVar("Result")


class PlaywrightWorkerPool:
    """Keeps a fixed number of pages available for concurrent browser operations."""

    def __init__(
        self,
        *,
        max_workers: int = 2,
        context_options: dict[str, Any] | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("Playwright worker count must be at least one.")
        self._max_workers = max_workers
        self._context_options = dict(context_options or {})
        self._pages: asyncio.Queue[Page] = asyncio.Queue(maxsize=max_workers)
        self._contexts: list[BrowserContext] = []
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> "PlaywrightWorkerPool":
        try:
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise RuntimeError(
                "Playwright is not installed. Install the browser extra before using this source."
            ) from error

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        for _ in range(self._max_workers):
            context = await self._browser.new_context(**self._context_options)
            self._contexts.append(context)
            await self._pages.put(await context.new_page())
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.close()

    async def run(self, operation: Callable[[Page], Awaitable[Result]]) -> Result:
        """Runs one operation with an exclusive reusable browser page."""
        page = await self._pages.get()
        try:
            return await operation(page)
        finally:
            await self._pages.put(page)

    async def close(self) -> None:
        """Closes browser resources even if a source operation failed."""
        for context in self._contexts:
            await context.close()
        self._contexts.clear()
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
