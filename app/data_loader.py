"""Carga paralela del CSV de ventas (Cruz Morada).

Paralelismo *propio* (no delegado a un motor externo), implementado en la fase
de carga tal como se acordó en CLAUDE.md (secciones 5 y 8):

1. El archivo se divide en *chunks* por **offsets de bytes**, alineados a fin
   de línea para no partir un registro por la mitad.
2. Cada chunk se reparte a un proceso *worker* vía ``ProcessPoolExecutor``.
   El worker abre el archivo, lee SOLO su rango de bytes, lo parsea con pandas
   y lo limpia/tipa. Así el I/O y el parseo ocurren en paralelo, no solo la
   limpieza.
3. El proceso principal concatena los DataFrames resultantes en una única
   estructura en memoria, que luego consultarán los endpoints.

Formato real del CSV (verificado sobre ``data/ventas_completas.csv``):
- Separador ``;`` (no ``,``).
- Campos entre comillas dobles.
- Cabeceras con espacios: ``PORCENTAJE DESCUENTO``, ``MONTO APLICADO``,
  ``CODIGO CLIENTE``, ``RUN CLIENTE``, ``FECHA NACIMIENTO``.
- ``GENERO`` numérico (1/2).

Supuesto de la partición por bytes: ningún campo contiene saltos de línea
embebidos dentro de las comillas. Es cierto para este dataset (fechas, montos,
nombres, UUIDs y RUTs), y es la condición estándar para poder trocear un CSV
por offsets de forma segura.
"""

from __future__ import annotations

import io
import os
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Esquema
# --------------------------------------------------------------------------- #

# Nombres tal como vienen en el archivo (con espacios).
RAW_COLUMNS: List[str] = [
    "FECHA",
    "CANAL",
    "SKU",
    "PRODUCTO",
    "UNIDADES",
    "PORCENTAJE DESCUENTO",
    "MONTO APLICADO",
    "BOLETA",
    "LOCAL",
    "CODIGO CLIENTE",
    "RUN CLIENTE",
    "NOMBRES",
    "APELLIDOS",
    "FECHA NACIMIENTO",
    "GENERO",
]

# Nombres canónicos (con guion bajo) usados por el resto de la aplicación.
RENAME_TO_CANONICAL = {
    "PORCENTAJE DESCUENTO": "PORCENTAJE_DESCUENTO",
    "MONTO APLICADO": "MONTO_APLICADO",
    "CODIGO CLIENTE": "CODIGO_CLIENTE",
    "RUN CLIENTE": "RUN_CLIENTE",
    "FECHA NACIMIENTO": "FECHA_NACIMIENTO",
}

# Tipos que el parser C de pandas puede asignar directamente (rápido).
# Las columnas de texto quedan como object; las fechas se parsean aparte.
_READ_DTYPES = {
    "SKU": "int32",
    "UNIDADES": "int16",
    "PORCENTAJE DESCUENTO": "float32",
    "MONTO APLICADO": "float64",  # métrica principal: float64 preserva la suma
    "BOLETA": "int64",
    "GENERO": "int8",
}

# Formatos de fecha explícitos → conversión vectorizada y rápida en pandas.
_FMT_FECHA = "%Y-%m-%dT%H:%M:%S"
_FMT_NACIMIENTO = "%Y-%m-%d"

# Etiquetas textuales de GENERO (enunciado). Cualquier valor no mapeado cae en
# "No especificado".
_GENERO_LABELS = {1: "Masculino", 2: "Femenino", 3: "Otro"}
_GENERO_DEFAULT = "No especificado"

# Columnas a convertir en categóricas al final (baja cardinalidad).
_CATEGORY_COLUMNS = ["CANAL", "LOCAL", "PRODUCTO", "GENERO"]

_SEP = ";"
_QUOTECHAR = '"'


# --------------------------------------------------------------------------- #
# Limpieza / tipado de un chunk
# --------------------------------------------------------------------------- #

def _derive_edad(fecha: pd.Series, nacimiento: pd.Series) -> pd.Series:
    """EDAD del cliente al momento de la venta (determinista fila a fila).

    Se calcula como los años cumplidos entre ``FECHA_NACIMIENTO`` y ``FECHA``
    de la operación. Es reproducible (no depende de "hoy") y no exige elegir
    una fecha de referencia arbitraria. Devuelve ``Int16`` nullable para tolerar
    fechas inválidas.
    """
    edad = fecha.dt.year - nacimiento.dt.year
    ya_cumplio = (fecha.dt.month > nacimiento.dt.month) | (
        (fecha.dt.month == nacimiento.dt.month) & (fecha.dt.day >= nacimiento.dt.day)
    )
    edad = edad - (~ya_cumplio).astype("int16")
    edad = edad.where(fecha.notna() & nacimiento.notna())
    return edad.astype("Int16")


def clean_chunk(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Limpia y tipa un chunk crudo (columnas ``RAW_COLUMNS``).

    Función pura y testeable: la usan tanto los workers como la carga
    secuencial, así que ambas rutas producen exactamente el mismo resultado.
    """
    df = df_raw

    # Fechas con formato explícito (mucho más rápido que la inferencia).
    fecha = pd.to_datetime(df["FECHA"], format=_FMT_FECHA, errors="coerce")
    nacimiento = pd.to_datetime(
        df["FECHA NACIMIENTO"], format=_FMT_NACIMIENTO, errors="coerce"
    )
    df["FECHA"] = fecha
    df["FECHA NACIMIENTO"] = nacimiento

    # EDAD derivada.
    df["EDAD"] = _derive_edad(fecha, nacimiento)

    # GENERO numérico → etiqueta textual.
    df["GENERO"] = (
        df["GENERO"].map(_GENERO_LABELS).fillna(_GENERO_DEFAULT).astype("object")
    )

    df = df.rename(columns=RENAME_TO_CANONICAL)
    return df


# --------------------------------------------------------------------------- #
# Partición por offsets de bytes
# --------------------------------------------------------------------------- #

def _compute_chunk_bounds(path: str, n_chunks: int) -> Tuple[bytes, List[Tuple[int, int]]]:
    """Divide el archivo en ``n_chunks`` rangos ``(start, end)`` de bytes.

    Cada frontera se ajusta al inicio de la siguiente línea completa, de modo
    que ningún rango parte un registro. La cabecera queda fuera de todos los
    rangos. Devuelve ``(header_bytes, [(start, end), ...])``.
    """
    file_size = os.path.getsize(path)
    with open(path, "rb") as f:
        header = f.readline()
        header_end = f.tell()

    n_chunks = max(1, n_chunks)
    data_size = file_size - header_end
    if data_size <= 0:
        return header, []

    step = data_size // n_chunks
    bounds: List[Tuple[int, int]] = []
    start = header_end
    with open(path, "rb") as f:
        for i in range(1, n_chunks):
            target = header_end + i * step
            if target <= start:
                continue
            f.seek(target)
            f.readline()  # avanza hasta el comienzo de la siguiente línea
            end = f.tell()
            if end > start and end < file_size:
                bounds.append((start, end))
                start = end
        bounds.append((start, file_size))
    return header, bounds


def _read_raw_range(path: str, start: int, end: int) -> pd.DataFrame:
    """Lee y parsea (sin limpiar) el rango de bytes ``[start, end)``."""
    with open(path, "rb") as f:
        f.seek(start)
        raw = f.read(end - start)
    return pd.read_csv(
        io.BytesIO(raw),
        sep=_SEP,
        quotechar=_QUOTECHAR,
        header=None,
        names=RAW_COLUMNS,
        dtype=_READ_DTYPES,
        keep_default_na=False,
        na_values=[""],
    )


def _process_range(task: Tuple[str, int, int]) -> pd.DataFrame:
    """Worker: lee su rango de bytes, lo parsea y lo limpia."""
    path, start, end = task
    df_raw = _read_raw_range(path, start, end)
    return clean_chunk(df_raw)


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ajustes finales sobre el DataFrame ya concatenado."""
    for col in _CATEGORY_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #

def load_csv(
    path: str,
    n_workers: Optional[int] = None,
    chunks_per_worker: int = 1,
) -> pd.DataFrame:
    """Carga el CSV en paralelo (chunking por bytes + ProcessPoolExecutor).

    Args:
        path: ruta al CSV.
        n_workers: número de procesos. Por defecto ``os.cpu_count()``.
        chunks_per_worker: cuántos chunks generar por worker. >1 mejora el
            balanceo de carga a costa de más overhead de serialización.

    Returns:
        DataFrame limpio y tipado, con columnas canónicas y ``EDAD`` derivada.
    """
    if n_workers is None:
        n_workers = os.cpu_count() or 1
    n_workers = max(1, n_workers)
    n_chunks = max(1, n_workers * max(1, chunks_per_worker))

    _, bounds = _compute_chunk_bounds(path, n_chunks)
    if not bounds:
        return _finalize(clean_chunk(_empty_raw()))

    tasks = [(path, start, end) for start, end in bounds]

    if n_workers == 1 or len(tasks) == 1:
        parts = [_process_range(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            parts = list(pool.map(_process_range, tasks))

    df = pd.concat(parts, ignore_index=True)
    return _finalize(df)


def load_csv_sequential(path: str) -> pd.DataFrame:
    """Carga el CSV en un solo proceso (baseline para comparar tiempos)."""
    df_raw = pd.read_csv(
        path,
        sep=_SEP,
        quotechar=_QUOTECHAR,
        header=0,
        names=RAW_COLUMNS,
        dtype=_READ_DTYPES,
        keep_default_na=False,
        na_values=[""],
    )
    return _finalize(clean_chunk(df_raw))


def _empty_raw() -> pd.DataFrame:
    """DataFrame vacío con las columnas crudas (para archivos sin datos)."""
    return pd.DataFrame({c: pd.Series(dtype="object") for c in RAW_COLUMNS})
