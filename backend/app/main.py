"""ConfiguraciÃ³n y creaciÃ³n de la aplicaciÃ³n FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_v1 import router as api_v1_router
from app.config import get_settings
from app.modules.ingestion.infrastructure.scheduler import ScrapingScheduler
from app.shared.infrastructure.database import async_session_factory
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.shared.interfaces.http import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Owns the optional background ingestion scheduler lifecycle."""
    settings = get_settings()
    scheduler: ScrapingScheduler | None = None
    if settings.ingestion_scheduler_enabled:
        scheduler = ScrapingScheduler(
            lambda: SQLAlchemyUnitOfWork(async_session_factory),
            poll_seconds=settings.ingestion_scheduler_poll_seconds,
            batch_size=settings.ingestion_scheduler_batch_size,
            max_concurrency=settings.ingestion_scheduler_max_concurrency,
            lease_seconds=settings.ingestion_scheduler_lease_seconds,
        )
        app.state.ingestion_scheduler = scheduler
        await scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()


def create_app() -> FastAPI:
    """Crea la aplicaciÃ³n y registra los adaptadores HTTP pÃºblicos."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        description="Backend DSS para la comparaciÃ³n de precios de supermercados.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_v1_router)
    return app


app = create_app()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Expone un estado mÃ­nimo para comprobar la disponibilidad del servicio."""
    return {"status": "ok", "service": "price-dss-backend"}
