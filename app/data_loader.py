# Carga paralela del CSV de ventas: chunking por offsets de bytes + ProcessPoolExecutor.

from __future__ import annotations

import io
import os
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

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

# Etiquetas textuales de GENERO. Cualquier valor no mapeado cae en "No especificado".
_GENERO_LABELS = {1: "Masculino", 2: "Femenino", 3: "Otro"}
_GENERO_DEFAULT = "No especificado"

# Columnas a convertir en categóricas al final (baja cardinalidad).
_CATEGORY_COLUMNS = ["CANAL", "LOCAL", "PRODUCTO", "GENERO"]

_SEP = ";"
_QUOTECHAR = '"'


# Calcula EDAD (años cumplidos) entre FECHA_NACIMIENTO y FECHA de la venta; Int16 nullable.
def _derive_edad(fecha: pd.Series, nacimiento: pd.Series) -> pd.Series:
    edad = fecha.dt.year - nacimiento.dt.year
    ya_cumplio = (fecha.dt.month > nacimiento.dt.month) | (
        (fecha.dt.month == nacimiento.dt.month) & (fecha.dt.day >= nacimiento.dt.day)
    )
    edad = edad - (~ya_cumplio).astype("int16")
    edad = edad.where(fecha.notna() & nacimiento.notna())
    return edad.astype("Int16")


# Limpia y tipa un chunk crudo (columnas RAW_COLUMNS); usada por workers y carga secuencial.
def clean_chunk(df_raw: pd.DataFrame) -> pd.DataFrame:
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


# Divide el archivo en n_chunks rangos (start, end) de bytes, alineados a fin de línea.
def _compute_chunk_bounds(path: str, n_chunks: int) -> Tuple[bytes, List[Tuple[int, int]]]:
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


# Lee y parsea (sin limpiar) el rango de bytes [start, end).
def _read_raw_range(path: str, start: int, end: int) -> pd.DataFrame:
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


# Worker: lee su rango de bytes, lo parsea y lo limpia.
def _process_range(task: Tuple[str, int, int]) -> pd.DataFrame:
    path, start, end = task
    df_raw = _read_raw_range(path, start, end)
    return clean_chunk(df_raw)


_COLUMNAS_SENSIBLES = ["RUN_CLIENTE", "NOMBRES", "APELLIDOS", "FECHA_NACIMIENTO", "BOLETA"]


# Convierte columnas de baja cardinalidad a category, elimina datos personales
# innecesarios y resetea el índice.
def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    for col in _CATEGORY_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")
    df = df.drop(columns=[c for c in _COLUMNAS_SENSIBLES if c in df.columns])
    return df.reset_index(drop=True)


# Carga el CSV en paralelo: reparte n_workers x chunks_per_worker rangos entre procesos worker.
def load_csv(
    path: str,
    n_workers: Optional[int] = None,
    chunks_per_worker: int = 1,
) -> pd.DataFrame:
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


# Carga el CSV en un solo proceso (baseline para comparar tiempos con load_csv).
def load_csv_sequential(path: str) -> pd.DataFrame:
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


# DataFrame vacío con las columnas crudas (para archivos sin datos).
def _empty_raw() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in RAW_COLUMNS})
