"""Handlers de GET y POST en `/v1/estadisticas/ventas` (CLAUDE.md §7, §9).

Orquestan: recibir consulta -> `filters.aplicar_filtros` -> `stats.calcular_estadisticas`
-> responder. Las excepciones (`filters.FiltroInvalidoError`,
`stats.SinDatosError`) se dejan propagar sin capturarlas acá: el módulo
`errors` las traduce, en un único lugar, al formato JSON exacto de 400/500
del enunciado.
"""

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

# Mapeo de campo de query param -> clave de filtro (mismos nombres que
# `TipoConsulta`, ver CLAUDE.md §7 tabla de filtros).
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


def _query_params_a_consultas(
    params: EstadisticasVentasQueryParams,
) -> List[ConsultaFiltro]:
    """Convierte los query params opcionales del GET a la misma lista de
    `ConsultaFiltro` que usa el POST, para reusar exactamente la misma
    lógica de filtrado en ambos métodos."""
    consultas = []
    for campo, clave in _CAMPO_A_CLAVE_FILTRO.items():
        valor = getattr(params, campo)
        if valor is not None:
            consultas.append(ConsultaFiltro(consulta=clave, valor=str(valor)))
    return consultas


def _resolver_estadisticas(consultas: List[ConsultaFiltro]) -> EstadisticasVentasResponse:
    df = data_store.get_ventas_df()
    subconjunto = filters.aplicar_filtros(df, consultas)
    resultado = stats.calcular_estadisticas(subconjunto[COLUMNA_METRICA])

    logger.success(
        "consulta resuelta: {} filtro(s), {} fila(s) coincidentes",
        len(consultas), resultado["conteo"],
    )
    return EstadisticasVentasResponse(**resultado)


@router.get("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse)
def obtener_estadisticas_ventas(
    params: EstadisticasVentasQueryParams = Depends(),
) -> EstadisticasVentasResponse:
    """Estadísticas de ventas con filtros predeterminados (query params)."""
    consultas = _query_params_a_consultas(params)
    return _resolver_estadisticas(consultas)


@router.post("/v1/estadisticas/ventas", response_model=EstadisticasVentasResponse)
def calcular_estadisticas_ventas(
    body: EstadisticasVentasRequest,
) -> EstadisticasVentasResponse:
    """Estadísticas de ventas con filtros personalizados (body JSON)."""
    return _resolver_estadisticas(body.consultas)
