"""Configuración centralizada obtenida desde el entorno de ejecución."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[3]
SQLITE_ASYNC_PREFIX = "sqlite+aiosqlite:///"
DEFAULT_DATABASE_URL = f"{SQLITE_ASYNC_PREFIX}{(BACKEND_ROOT / 'price_dss_demo.db').as_posix()}"


class Settings(BaseSettings):
    """Valores técnicos de la aplicación; no contiene configuración de módulos."""

    app_name: str = "price-dss-backend"
    environment: str = "development"
    debug: bool = True
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
    )

    @field_validator("database_url")
    @classmethod
    def resolve_relative_sqlite_database_url(cls, database_url: str) -> str:
        """Keeps SQLite commands on one database regardless of the current directory."""
        if not database_url.startswith(SQLITE_ASYNC_PREFIX):
            return database_url

        database_path = database_url.removeprefix(SQLITE_ASYNC_PREFIX)
        if database_path == ":memory:" or Path(database_path).is_absolute():
            return database_url

        return f"{SQLITE_ASYNC_PREFIX}{(BACKEND_ROOT / database_path).resolve().as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """Obtiene una instancia de configuración reutilizable durante la ejecución."""
    return Settings()
