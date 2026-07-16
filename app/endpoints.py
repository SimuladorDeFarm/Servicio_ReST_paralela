# Handlers GET/POST de /v1/estadisticas/ventas: filters -> stats -> responder.
# Las excepciones se dejan propagar; el módulo errors las traduce al formato JSON exacto.

from typing import List

from fastapi import APIRouter, Depends

from app import data_store, filters, stats
from app.logging_config import logger
from app.schemas import (
    ConsultaFiltro,
    EstadisticasVentasQueryParams,
    EstadisticasVentasRequest,
    EstadisticasVentasResponse,
)

router = APIRouter()

COLUMNA_METRICA = "MONTO_APLICADO"

# Mapeo de campo de query param -> clave de filtro (mismos nombres que TipoConsulta).
_CAMPO_A_CLAVE_FILTRO = {
    "genero": "GENERO",
    "edad": "EDAD",
    "canal": "CANAL",
    "codigo_producto": "CODIGO_PRODUCTO",
    "id_persona": "ID_PERSONA",
    "local": "LOCAL",
    "fecha_desde": "FECHA_DESDE",
    "fecha_hasta": "FECHA_HASTA",
}


# Convierte los query params opcionales del GET a la misma lista de ConsultaFiltro que usa el POST.
def _query_params_a_consultas(
    params: EstadisticasVentasQueryParams,
) -> List[ConsultaFiltro]:
    consultas = []
    for campo, clave in _CAMPO_A_CLAVE_FILTRO.items():
        valor = getattr(params, campo)
        if valor is not None:
            consultas.append(ConsultaFiltro(consulta=clave, valor=str(valor)))
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
@router.get("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse)
def obtener_estadisticas_ventas(
    params: EstadisticasVentasQueryParams = Depends(),
) -> EstadisticasVentasResponse:
    consultas = _query_params_a_consultas(params)
    return _resolver_estadisticas(consultas)


# POST: estadísticas de ventas con filtros personalizados (body JSON).
@router.post("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse)
def calcular_estadisticas_ventas(
    body: EstadisticasVentasRequest,
) -> EstadisticasVentasResponse:
    return _resolver_estadisticas(body.consultas)
