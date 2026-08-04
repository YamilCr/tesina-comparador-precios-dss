"""Manejadores HTTP para normalizar respuestas de error."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _message_from_detail(detail: Any, fallback: str) -> str:
    """Obtiene un mensaje legible sin descartar el detalle original."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str):
            return message
    return fallback


def _error_payload(
    *,
    code: str,
    message: str,
    detail: Any,
) -> dict[str, Any]:
    """Construye el contrato de error manteniendo `detail` por compatibilidad."""
    encoded_detail = jsonable_encoder(detail)
    return {
        "detail": encoded_detail,
        "error": {
            "code": code,
            "message": message,
            "details": encoded_detail,
        },
    }


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Convierte HTTPException al contrato de error del backend."""
    message = _message_from_detail(exc.detail, "HTTP request failed.")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            code="http_error",
            message=message,
            detail=exc.detail,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convierte errores de validación al contrato de error del backend."""
    detail = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_payload(
            code="validation_error",
            message="Request validation failed.",
            detail=detail,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra manejadores de errores HTTP compartidos."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
