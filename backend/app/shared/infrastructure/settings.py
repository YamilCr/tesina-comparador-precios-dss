"""Configuración centralizada obtenida desde el entorno de ejecución."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores técnicos de la aplicación; no contiene configuración de módulos."""

    app_name: str = "price-dss-backend"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/price_dss"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Obtiene una instancia de configuración reutilizable durante la ejecución."""
    return Settings()
