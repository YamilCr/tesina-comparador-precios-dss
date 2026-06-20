"""Configuración y creación de la aplicación FastAPI."""

from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    """Crea la aplicación base sin registrar lógica de negocio."""
    settings = get_settings()
    return FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        description="Backend DSS para la comparación de precios de supermercados.",
    )


app = create_app()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Expone un estado mínimo para comprobar la disponibilidad del servicio."""
    return {"status": "ok", "service": "price-dss-backend"}
