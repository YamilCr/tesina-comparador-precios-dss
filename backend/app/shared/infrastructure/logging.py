"""Configuración de logging común para los adaptadores de infraestructura."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configura un formato mínimo de logs para la aplicación."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
