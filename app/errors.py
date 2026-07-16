"""Excepciones custom + exception handlers globales (CLAUDE.md §7, §9).

Arma el JSON de error EXACTO pedido por el enunciado para 400 y 500, sin
importar en qué capa se originó la falla:

- `filters.FiltroInvalidoError`  -> 400, errorCode "VF"  (valor no convertible).
- `RequestValidationError`       -> 400, errorCode "VF"  (clave no reconocida,
  tipo de dato incorrecto en query params/body — lo detecta Pydantic/FastAPI
  antes de llegar a nuestro código).
- `stats.SinDatosError`          -> 500, errorCode "IE"  (error de cálculo,
  ej. desviación estándar sobre un conjunto vacío).
- Cualquier otra excepción no prevista -> 500, errorCode "IE" (red de
  seguridad: nunca debe filtrarse una respuesta sin el formato del enunciado).

`endpoints.py` ya no atrapa estas excepciones: las deja propagar y este
módulo las traduce, en un único lugar, al formato de respuesta acordado.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import filters, stats
from app.logging_config import logger

_MDN_STATUS_URL = "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/{}"

_TITULOS = {
    status.HTTP_400_BAD_REQUEST: "Bad Request",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal Server Error",
}


def _timestamp() -> str:
    """Timestamp ISO-8601 UTC con sufijo 'Z'.

    Python solo entrega precisión de microsegundos (6 dígitos); se rellena
    con ceros hasta 9 dígitos para calzar con el formato del ejemplo del
    enunciado, sin pretender una precisión de nanosegundos que no se tiene.
    """
    ahora = datetime.now(timezone.utc)
    return ahora.strftime("%Y-%m-%dT%H:%M:%S.%f") + "000Z"


def _cuerpo_error(
    *,
    request: Request,
    status_code: int,
    detail: str,
    error_code: str,
    error_label: str,
) -> dict:
    return {
        "detail": detail,
        "instance": request.url.path,
        "status": status_code,
        "title": _TITULOS[status_code],
        "type": _MDN_STATUS_URL.format(status_code),
        "timestamp": _timestamp(),
        "errorCode": error_code,
        "errorLabel": error_label,
        "method": request.method,
    }


def _resumir_errores_validacion(exc: RequestValidationError) -> str:
    """Arma un `detail` legible a partir de los errores de Pydantic/FastAPI."""
    partes: List[str] = []
    for err in exc.errors():
        campo = ".".join(str(p) for p in err["loc"] if p not in ("body", "query"))
        partes.append(f"{campo}: {err['msg']}")
    return "; ".join(partes) if partes else "solicitud inválida"


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los exception handlers globales sobre `app`."""

    @app.exception_handler(filters.FiltroInvalidoError)
    async def _handle_filtro_invalido(request: Request, exc: filters.FiltroInvalidoError):
        logger.warning("400 (VF) en {} {}: {}", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_cuerpo_error(
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
                error_code="VF",
                error_label="Validación Fallida",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validacion_fastapi(request: Request, exc: RequestValidationError):
        detail = _resumir_errores_validacion(exc)
        logger.warning("400 (VF) en {} {}: {}", request.method, request.url.path, detail)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_cuerpo_error(
                request=request,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
                error_code="VF",
                error_label="Validación Fallida",
            ),
        )

    @app.exception_handler(stats.SinDatosError)
    async def _handle_sin_datos(request: Request, exc: stats.SinDatosError):
        logger.error("500 (IE) en {} {}: {}", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_cuerpo_error(
                request=request,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
                error_code="IE",
                error_label="Error Interno",
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_excepcion_no_prevista(request: Request, exc: Exception):
        logger.exception("500 (IE) no previsto en {} {}", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_cuerpo_error(
                request=request,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno inesperado",
                error_code="IE",
                error_label="Error Interno",
            ),
        )
