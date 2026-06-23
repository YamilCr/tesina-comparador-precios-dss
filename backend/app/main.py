"""ConfiguraciÃ³n y creaciÃ³n de la aplicaciÃ³n FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_v1 import router as api_v1_router
from app.config import get_settings


def create_app() -> FastAPI:
    """Crea la aplicaciÃ³n y registra los adaptadores HTTP pÃºblicos."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        description="Backend DSS para la comparaciÃ³n de precios de supermercados.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router)
    return app


app = create_app()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Expone un estado mÃ­nimo para comprobar la disponibilidad del servicio."""
    return {"status": "ok", "service": "price-dss-backend"}
