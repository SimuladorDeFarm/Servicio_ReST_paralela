"""Pruebas del data_store: singleton en memoria del DataFrame de ventas."""

import pandas as pd
import pytest

from app import data_store


@pytest.fixture(autouse=True)
def _reset_store():
    """Aísla cada test: limpia el singleton antes y después de correr."""
    data_store._ventas_df = None
    yield
    data_store._ventas_df = None


def test_get_antes_de_cargar_lanza_error():
    assert data_store.is_loaded() is False
    with pytest.raises(RuntimeError):
        data_store.get_ventas_df()


def test_set_y_get_devuelve_el_mismo_dataframe():
    df = pd.DataFrame({"MONTO_APLICADO": [1.0, 2.0]})
    data_store.set_ventas_df(df)

    assert data_store.is_loaded() is True
    assert data_store.get_ventas_df() is df


def test_get_es_accesible_como_singleton_entre_modulos():
    """Simula el acceso desde un endpoint: importa el módulo de nuevo y lee."""
    df = pd.DataFrame({"MONTO_APLICADO": [10.0]})
    data_store.set_ventas_df(df)

    from app import data_store as data_store_reimportado

    assert data_store_reimportado.get_ventas_df() is df
