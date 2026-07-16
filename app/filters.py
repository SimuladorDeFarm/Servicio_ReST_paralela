"""Validación y aplicación de los filtros soportados (CLAUDE.md §7, §9).

Cada filtro soportado tiene una función que valida/convierte el `valor`
textual y construye la máscara booleana correspondiente sobre el DataFrame
de ventas ya cargado. `aplicar_filtros` combina todos los filtros de una
consulta con AND y devuelve el subconjunto resultante.

Mapeo de claves de filtro a columnas del DataFrame (`data_loader`):
- GENERO            -> GENERO (etiqueta textual ya normalizada)
- EDAD              -> EDAD (derivada de FECHA_NACIMIENTO)
- CANAL             -> CANAL
- CODIGO_PRODUCTO   -> SKU (identificador único de producto)
- ID_PERSONA        -> CODIGO_CLIENTE (UUID)
- LOCAL             -> LOCAL
- FECHA_DESDE/HASTA -> FECHA (límites inclusivos)
"""

from typing import Callable, Dict, List

import pandas as pd

from app.schemas import ConsultaFiltro, TipoConsulta

GENEROS_VALIDOS = {"No especificado", "Masculino", "Femenino", "Otro"}
CANALES_VALIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}


class FiltroInvalidoError(ValueError):
    """Un filtro trae un valor no convertible al tipo esperado.

    El módulo `errors` (paso siguiente del roadmap) traducirá esta excepción
    a un 400 con `errorCode: "VF"` (Validación Fallida), tal como especifica
    el enunciado.
    """


def _mask_genero(df: pd.DataFrame, valor: str) -> pd.Series:
    if valor not in GENEROS_VALIDOS:
        raise FiltroInvalidoError(
            f"GENERO debe ser uno de {sorted(GENEROS_VALIDOS)}, se recibió '{valor}'"
        )
    return df["GENERO"] == valor


def _mask_edad(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        edad = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(f"EDAD debe ser un entero, se recibió '{valor}'")
    return df["EDAD"] == edad


def _mask_canal(df: pd.DataFrame, valor: str) -> pd.Series:
    if valor not in CANALES_VALIDOS:
        raise FiltroInvalidoError(
            f"CANAL debe ser uno de {sorted(CANALES_VALIDOS)}, se recibió '{valor}'"
        )
    return df["CANAL"] == valor


def _mask_codigo_producto(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        sku = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(
            f"CODIGO_PRODUCTO debe ser un entero (SKU), se recibió '{valor}'"
        )
    return df["SKU"] == sku


def _mask_id_persona(df: pd.DataFrame, valor: str) -> pd.Series:
    if not valor:
        raise FiltroInvalidoError("ID_PERSONA no puede ser vacío")
    return df["CODIGO_CLIENTE"] == valor


def _mask_local(df: pd.DataFrame, valor: str) -> pd.Series:
    try:
        local = int(valor)
    except (TypeError, ValueError):
        raise FiltroInvalidoError(f"LOCAL debe ser un entero, se recibió '{valor}'")
    return df["LOCAL"] == local


def _parse_fecha(valor: str, clave: str) -> pd.Timestamp:
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        raise FiltroInvalidoError(
            f"{clave} debe ser una fecha ISO-8601 válida, se recibió '{valor}'"
        )
    return fecha


def _mask_fecha_desde(df: pd.DataFrame, valor: str) -> pd.Series:
    return df["FECHA"] >= _parse_fecha(valor, "FECHA_DESDE")


def _mask_fecha_hasta(df: pd.DataFrame, valor: str) -> pd.Series:
    return df["FECHA"] <= _parse_fecha(valor, "FECHA_HASTA")


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


def aplicar_filtros(df: pd.DataFrame, filtros: List[ConsultaFiltro]) -> pd.DataFrame:
    """Aplica todos los `filtros` combinados con AND y devuelve el subconjunto.

    Con `filtros` vacío devuelve `df` completo (sin filtrar) — el enunciado
    permite consultas sin filtros, que entregan el total sin restringir.
    """
    mascara = pd.Series(True, index=df.index)
    for filtro in filtros:
        constructor = _CONSTRUCTORES_MASCARA[filtro.consulta]
        mascara_filtro = constructor(df, filtro.valor).fillna(False)
        mascara &= mascara_filtro
    return df[mascara]
