"""Tests for stable database configuration across command working directories."""

from app.shared.infrastructure.settings import BACKEND_ROOT, SQLITE_ASYNC_PREFIX, Settings


def test_relative_sqlite_url_is_anchored_to_backend_root() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///./isolated_demo.db")

    assert settings.database_url == (
        f"{SQLITE_ASYNC_PREFIX}{(BACKEND_ROOT / 'isolated_demo.db').as_posix()}"
    )


def test_in_memory_sqlite_url_is_not_rewritten() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")

    assert settings.database_url == "sqlite+aiosqlite:///:memory:"
