"""Dependencias de FastAPI que conectarán los adaptadores con la aplicación."""

from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings

SettingsDependency = Annotated[Settings, Depends(get_settings)]
