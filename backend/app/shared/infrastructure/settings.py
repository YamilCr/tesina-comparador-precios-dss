"""Configuración centralizada obtenida desde el entorno de ejecución."""

from functools import lru_cache
from pydantic import Field
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
    ingestion_scheduler_enabled: bool = True
    ingestion_scheduler_embedded_enabled: bool = True
    ingestion_scheduler_poll_seconds: int = Field(default=30, ge=1, le=3600)
    ingestion_scheduler_batch_size: int = Field(default=10, ge=1, le=100)
    ingestion_scheduler_max_concurrency: int = Field(default=3, ge=1, le=10)
    ingestion_scheduler_lease_seconds: int = Field(default=900, ge=60, le=7200)
    vector_search_enabled: bool = True
    vector_embedding_model: str = "intfloat/multilingual-e5-small"
    vector_embedding_dimensions: int = Field(default=384, ge=1, le=4096)
    vector_search_min_score: float = Field(default=0.35, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
    )

    @field_validator("database_url")
    @classmethod
    def resolve_relative_sqlite_database_url(cls, database_url: str) -> str:
        """Keeps SQLite commands on one database regardless of the current directory."""
        if database_url.startswith("postgresql://"):
            # Managed providers such as Render expose a standard PostgreSQL URL.
            # The application uses SQLAlchemy's asyncpg driver at runtime.
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
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
