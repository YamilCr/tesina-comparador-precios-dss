"""Adaptador de configuración de la aplicación hacia la infraestructura compartida."""

from app.shared.infrastructure.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
