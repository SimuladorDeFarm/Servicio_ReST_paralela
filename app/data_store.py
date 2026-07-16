"""Contenedor en memoria del DataFrame de ventas ya cargado y limpio.

Singleton a nivel de módulo (CLAUDE.md §9): `data_loader` lo llena una única
vez durante el arranque de la app (`lifespan` de FastAPI, ver `app/main.py`).
El resto de los módulos (`filters`, `stats`, `endpoints`) solo lo leen a
través de `get_ventas_df`, sin depender de `app.state` ni importar `main`
(evita import circular con los routers).
"""

from typing import Optional

import pandas as pd

_ventas_df: Optional[pd.DataFrame] = None


def set_ventas_df(df: pd.DataFrame) -> None:
    """Establece el DataFrame cargado. Se llama una sola vez, en el startup."""
    global _ventas_df
    _ventas_df = df


def get_ventas_df() -> pd.DataFrame:
    """Devuelve el DataFrame de ventas ya cargado.

    Lanza ``RuntimeError`` si se llama antes de que `data_loader` haya
    corrido (por ejemplo, un endpoint invocado fuera del ciclo de vida
    normal de la app).
    """
    if _ventas_df is None:
        raise RuntimeError(
            "El DataFrame de ventas aún no ha sido cargado "
            "(data_store.set_ventas_df no se ha ejecutado)."
        )
    return _ventas_df


def is_loaded() -> bool:
    return _ventas_df is not None
