"""Configuración centralizada obtenida desde el entorno de ejecución."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores técnicos de la aplicación; no contiene configuración de módulos."""

    app_name: str = "DSS Comparador de Precios"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./dss.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Obtiene una instancia de configuración reutilizable durante la ejecución."""
    return Settings()
