# Valida y aplica los 8 filtros soportados sobre el DataFrame de ventas ya cargado.
#
# Mapeo de filtro -> columna: GENERO->GENERO, EDAD->EDAD, CANAL->CANAL,
# CODIGO_PRODUCTO->SKU, ID_PERSONA->CODIGO_CLIENTE, LOCAL->LOCAL,
# FECHA_DESDE/HASTA->FECHA (límites inclusivos).

from typing import Callable, Dict, List

import pandas as pd

from app.schemas import ConsultaFiltro, TipoConsulta

GENEROS_VALIDOS = {"No especificado", "Masculino", "Femenino", "Otro"}
CANALES_VALIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}


# Valor no convertible al tipo esperado o fuera de los valores permitidos -> 400 (VF).
class FiltroInvalidoError(ValueError):
    pass


# GENERO: coincidencia exacta con una de las 4 etiquetas válidas.
def _mask_genero(df: pd.DataFrame, valor: str) -> pd.Series:
    if valor not in GENEROS_VALIDOS:
        raise FiltroInvalidoError(
            f"GENERO debe ser uno de {sorted(GENEROS_VALIDOS)}, se recibió '{valor}'"
        )
    return df["GENERO"] == valor


# EDAD: convierte a entero y compara contra la columna EDAD derivada.
def _mask_edad(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        edad = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(f"EDAD debe ser un entero, se recibió '{valor}'")
    return df["EDAD"] == edad


# CANAL: coincidencia exacta con uno de los 6 canales válidos.
def _mask_canal(df: pd.DataFrame, valor: str) -> pd.Series:
    if valor not in CANALES_VALIDOS:
        raise FiltroInvalidoError(
            f"CANAL debe ser uno de {sorted(CANALES_VALIDOS)}, se recibió '{valor}'"
        )
    return df["CANAL"] == valor


# CODIGO_PRODUCTO: convierte a entero y compara contra SKU.
def _mask_codigo_producto(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        sku = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(
            f"CODIGO_PRODUCTO debe ser un entero (SKU), se recibió '{valor}'"
        )
    return df["SKU"] == sku


# ID_PERSONA: coincidencia exacta de string (UUID) contra CODIGO_CLIENTE, no vacío.
def _mask_id_persona(df: pd.DataFrame, valor: str) -> pd.Series:
    if not valor:
        raise FiltroInvalidoError("ID_PERSONA no puede ser vacío")
    return df["CODIGO_CLIENTE"] == valor


# LOCAL: convierte a entero y compara contra la columna LOCAL.
def _mask_local(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        local = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(f"LOCAL debe ser un entero, se recibió '{valor}'")
    return df["LOCAL"] == local


# Parsea una fecha ISO-8601; lanza FiltroInvalidoError si no es convertible.
def _parse_fecha(valor: str, clave: str) -> pd.Timestamp:
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        raise FiltroInvalidoError(
            f"{clave} debe ser una fecha ISO-8601 válida, se recibió '{valor}'"
        )
    return fecha


# FECHA_DESDE: límite inferior inclusivo sobre la columna FECHA.
def _mask_fecha_desde(df: pd.DataFrame, valor: str) -> pd.Series:
    return df["FECHA"] >= _parse_fecha(valor, "FECHA_DESDE")


# FECHA_HASTA: límite superior inclusivo sobre la columna FECHA.
def _mask_fecha_hasta(df: pd.DataFrame, valor: str) -> pd.Series:
    return df["FECHA"] <= _parse_fecha(valor, "FECHA_HASTA")


# Tabla de despacho: clave de filtro -> función que construye su máscara.
_CONSTRUCTORES_MASCARA: Dict[TipoConsulta, Callable[[pd.DataFrame, str], pd.Series]] = {
    TipoConsulta.GENERO: _mask_genero,
    TipoConsulta.EDAD: _mask_edad,
    TipoConsulta.CANAL: _mask_canal,
    TipoConsulta.CODIGO_PRODUCTO: _mask_codigo_producto,
    TipoConsulta.ID_PERSONA: _mask_id_persona,
    TipoConsulta.LOCAL: _mask_local,
    TipoConsulta.FECHA_DESDE: _mask_fecha_desde,
    TipoConsulta.FECHA_HASTA: _mask_fecha_hasta,
}


# Combina todos los filtros con AND (fillna(False) evita que NaN/NaT rompan el indexado
# booleano) y devuelve el subconjunto resultante; lista vacía devuelve el DataFrame completo.
def aplicar_filtros(df: pd.DataFrame, filtros: List[ConsultaFiltro]) -> pd.DataFrame:
    mascara = pd.Series(True, index=df.index)
    for filtro in filtros:
        constructor = _CONSTRUCTORES_MASCARA[filtro.consulta]
        mascara_filtro = constructor(df, filtro.valor).fillna(False)
        mascara &= mascara_filtro
    return df[mascara]
