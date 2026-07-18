"""Pruebas de filters: cada filtro soportado, valores inválidos y combinación
AND de varios filtros, sobre la fixture pequeña (5 filas, valores conocidos).
"""

from pathlib import Path

import pandas as pd
import pytest

from app import data_loader, filters
from app.schemas import ConsultaFiltro

FIXTURE = Path(__file__).parent / "fixtures" / "ventas_prueba.csv"


@pytest.fixture(scope="module")
def df():
    return data_loader.load_csv_sequential(str(FIXTURE))


def test_sin_filtros_devuelve_todo(df):
    resultado = filters.aplicar_filtros(df, [])
    assert len(resultado) == 5


def test_filtro_genero(df):
    resultado = filters.aplicar_filtros(
        df, [ConsultaFiltro(consulta="GENERO", valor="Masculino")]
    )
    assert len(resultado) == 2
    assert resultado["MONTO_APLICADO"].sum() == 4000.0


def test_filtro_genero_no_especificado(df):
    resultado = filters.aplicar_filtros(
        df, [ConsultaFiltro(consulta="GENERO", valor="No especificado")]
    )
    assert len(resultado) == 1
    assert resultado["MONTO_APLICADO"].iloc[0] == 500.0


def test_filtro_genero_invalido_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="GENERO", valor="Alien")])


def test_filtro_edad(df):
    resultado = filters.aplicar_filtros(df, [ConsultaFiltro(consulta="EDAD", valor="33")])
    assert len(resultado) == 1
    assert resultado["MONTO_APLICADO"].iloc[0] == 1000.0


def test_filtro_edad_no_convertible_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="EDAD", valor="treinta")])


def test_filtro_canal(df):
    resultado = filters.aplicar_filtros(df, [ConsultaFiltro(consulta="CANAL", valor="POS")])
    assert len(resultado) == 2
    assert resultado["MONTO_APLICADO"].sum() == 4000.0


def test_filtro_canal_invalido_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="CANAL", valor="FAX")])


def test_filtro_codigo_producto(df):
    resultado = filters.aplicar_filtros(
        df, [ConsultaFiltro(consulta="CODIGO_PRODUCTO", valor="100")]
    )
    assert len(resultado) == 2
    assert resultado["MONTO_APLICADO"].sum() == 4000.0


def test_filtro_id_persona(df):
    resultado = filters.aplicar_filtros(
        df,
        [
            ConsultaFiltro(
                consulta="ID_PERSONA",
                valor="11111111-1111-4111-8111-111111111111",
            )
        ],
    )
    assert len(resultado) == 1
    assert resultado["MONTO_APLICADO"].iloc[0] == 1000.0


def test_filtro_id_persona_vacio_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="ID_PERSONA", valor="")])


def test_filtro_codigo_producto_no_convertible_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(
            df, [ConsultaFiltro(consulta="CODIGO_PRODUCTO", valor="no-es-un-sku")]
        )


def test_filtro_local(df):
    resultado = filters.aplicar_filtros(df, [ConsultaFiltro(consulta="LOCAL", valor="371")])
    assert len(resultado) == 3
    assert resultado["MONTO_APLICADO"].sum() == 4500.0


def test_filtro_local_no_convertible_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="LOCAL", valor="abc")])


def test_filtro_fecha_desde_hasta(df):
    resultado = filters.aplicar_filtros(
        df,
        [
            ConsultaFiltro(consulta="FECHA_DESDE", valor="2023-06-01"),
            ConsultaFiltro(consulta="FECHA_HASTA", valor="2023-07-01"),
        ],
    )
    assert len(resultado) == 2
    assert resultado["MONTO_APLICADO"].sum() == 3500.0


def test_filtro_fecha_invalida_lanza_error(df):
    with pytest.raises(filters.FiltroInvalidoError):
        filters.aplicar_filtros(df, [ConsultaFiltro(consulta="FECHA_DESDE", valor="no-es-fecha")])


def test_combinacion_and_de_varios_filtros(df):
    resultado = filters.aplicar_filtros(
        df,
        [
            ConsultaFiltro(consulta="GENERO", valor="Femenino"),
            ConsultaFiltro(consulta="CANAL", valor="WEB"),
        ],
    )
    assert len(resultado) == 1
    assert resultado["MONTO_APLICADO"].iloc[0] == 2500.0


def test_combinacion_sin_coincidencias_devuelve_vacio(df):
    resultado = filters.aplicar_filtros(
        df,
        [
            ConsultaFiltro(consulta="GENERO", valor="Femenino"),
            ConsultaFiltro(consulta="CANAL", valor="APP"),
        ],
    )
    assert len(resultado) == 0
