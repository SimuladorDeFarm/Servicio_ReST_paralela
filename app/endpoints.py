# Handlers GET/POST de /v1/estadisticas/ventas: filters -> stats -> responder.
# Las excepciones se dejan propagar; el módulo errors las traduce al formato JSON exacto.

from typing import List

from fastapi import APIRouter, Depends

from app import data_store, filters, stats
from app.auth import verificar_api_key
from app.logging_config import logger
from app.schemas import (
    ConsultaFiltro,
    ErrorResponse,
    EstadisticasVentasQueryParams,
    EstadisticasVentasRequest,
    EstadisticasVentasResponse,
)

_RESPONSES_ERROR = {
    400: {"model": ErrorResponse, "description": "Filtro inválido (VF)"},
    500: {"model": ErrorResponse, "description": "Error interno (IE)"},
}

router = APIRouter(dependencies=[Depends(verificar_api_key)])

COLUMNA_METRICA = "MONTO_APLICADO"

# Campos de query param que corresponden a claves de filtro.
_CAMPOS_FILTRO = [
    "GENERO", "EDAD", "CANAL", "CODIGO_PRODUCTO",
    "ID_PERSONA", "LOCAL", "FECHA_DESDE", "FECHA_HASTA",
]


# Convierte los query params opcionales del GET a la misma lista de ConsultaFiltro que usa el POST.
def _query_params_a_consultas(
    params: EstadisticasVentasQueryParams,
) -> List[ConsultaFiltro]:
    consultas = []
    for campo in _CAMPOS_FILTRO:
        valor = getattr(params, campo)
        if valor is not None:
            consultas.append(ConsultaFiltro(consulta=campo, valor=str(valor)))
    return consultas


# Aplica los filtros sobre el DataFrame cargado y calcula las estadísticas del subconjunto.
def _resolver_estadisticas(consultas: List[ConsultaFiltro]) -> EstadisticasVentasResponse:
    df = data_store.get_ventas_df()
    subconjunto = filters.aplicar_filtros(df, consultas)
    resultado = stats.calcular_estadisticas(subconjunto[COLUMNA_METRICA])

    logger.success(
        "consulta resuelta: {} filtro(s), {} fila(s) coincidentes",
        len(consultas), resultado["conteo"],
    )
    return EstadisticasVentasResponse(**resultado)


# GET: estadísticas de ventas con filtros predeterminados (query params).
@router.get("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse, responses=_RESPONSES_ERROR)
def obtener_estadisticas_ventas(
    params: EstadisticasVentasQueryParams = Depends(),
) -> EstadisticasVentasResponse:
    consultas = _query_params_a_consultas(params)
    return _resolver_estadisticas(consultas)


# POST: estadísticas de ventas con filtros personalizados (body JSON).
@router.post("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse, responses=_RESPONSES_ERROR)
def calcular_estadisticas_ventas(
    body: EstadisticasVentasRequest,
) -> EstadisticasVentasResponse:
    return _resolver_estadisticas(body.consultas)
