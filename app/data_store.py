# Singleton en memoria del DataFrame de ventas: data_loader lo llena una vez, el resto lo lee.

from typing import Optional

import pandas as pd

_ventas_df: Optional[pd.DataFrame] = None


# Guarda el DataFrame cargado (se llama una sola vez, en el startup de la app).
def set_ventas_df(df: pd.DataFrame) -> None:
    global _ventas_df
    _ventas_df = df


# Devuelve el DataFrame ya cargado; lanza RuntimeError si aún no se cargó.
def get_ventas_df() -> pd.DataFrame:
    if _ventas_df is None:
        raise RuntimeError(
            "El DataFrame de ventas aún no ha sido cargado "
            "(data_store.set_ventas_df no se ha ejecutado)."
        )
    return _ventas_df


# True si el DataFrame ya fue cargado.
def is_loaded() -> bool:
    return _ventas_df is not None
