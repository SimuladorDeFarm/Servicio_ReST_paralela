# Exception handlers globales: arman el JSON de error exacto (400/500) sin importar
# en qué capa se originó la falla (filters, stats, validación de Pydantic, o no prevista).

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


# Timestamp ISO-8601 UTC con sufijo Z (relleno a 9 dígitos para calzar el formato pedido).
def _timestamp() -> str:
    ahora = datetime.now(timezone.utc)
    return ahora.strftime("%Y-%m-%dT%H:%M:%S.%f") + "000Z"


# Arma el dict con los 9 campos exactos del formato de error del enunciado.
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


# Arma un detail legible a partir de los errores de validación de Pydantic/FastAPI.
def _resumir_errores_validacion(exc: RequestValidationError) -> str:
    partes: List[str] = []
    for err in exc.errors():
        campo = ".".join(str(p) for p in err["loc"] if p not in ("body", "query"))
        partes.append(f"{campo}: {err['msg']}")
    return "; ".join(partes) if partes else "solicitud inválida"


# Registra los 4 exception handlers globales sobre app.
def register_exception_handlers(app: FastAPI) -> None:

    # 400: filtro con valor no convertible o fuera de rango (ej. CANAL="FAX").
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

    # 400: clave de filtro no reconocida o tipo de dato incorrecto (validación de Pydantic).
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

    # 500: filtros válidos pero sin filas coincidentes (métricas indefinidas).
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

    # 500: red de seguridad para cualquier excepción no prevista.
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
