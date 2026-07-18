"""Pruebas de stats: cada métrica se verifica con valores conocidos,
calculados a mano, cubriendo conteo par/impar, un solo elemento y vacío.
"""

import math

import pandas as pd
import pytest

from app import stats


# --------------------------------------------------------------------------- #
# Conteo impar: [10, 20, 30, 40, 100]
# suma=200, promedio=40, mediana=30 (centro), min=10, max=100
# varianza poblacional = mean((x-40)^2) = (900+400+100+0+3600)/5 = 1000
# std = sqrt(1000) = 31.6227766017...
# --------------------------------------------------------------------------- #

@pytest.fixture
def valores_impar():
    return pd.Series([10.0, 20.0, 30.0, 40.0, 100.0])


def test_conteo_impar(valores_impar):
    assert stats.conteo(valores_impar) == 5


def test_suma_impar(valores_impar):
    assert stats.suma(valores_impar) == 200.0


def test_promedio_impar(valores_impar):
    assert stats.promedio(valores_impar) == 40.0


def test_minimo_impar(valores_impar):
    assert stats.minimo(valores_impar) == 10.0


def test_maximo_impar(valores_impar):
    assert stats.maximo(valores_impar) == 100.0


def test_mediana_impar(valores_impar):
    assert stats.mediana(valores_impar) == 30.0


def test_desviacion_estandar_impar(valores_impar):
    assert stats.desviacion_estandar(valores_impar) == pytest.approx(math.sqrt(1000))


def test_calcular_estadisticas_impar(valores_impar):
    resultado = stats.calcular_estadisticas(valores_impar)
    assert resultado == {
        "suma": 200.0,
        "conteo": 5,
        "promedio": 40.0,
        "minimo": 10.0,
        "maximo": 100.0,
        "mediana": 30.0,
        "desviacion_estandar": pytest.approx(math.sqrt(1000)),
    }


# --------------------------------------------------------------------------- #
# Conteo par: [10, 20, 30, 40]
# suma=100, promedio=25, mediana=(20+30)/2=25, min=10, max=40
# varianza poblacional = mean((x-25)^2) = (225+25+25+225)/4 = 125
# std = sqrt(125) = 11.1803398875...
# --------------------------------------------------------------------------- #

@pytest.fixture
def valores_par():
    return pd.Series([10.0, 20.0, 30.0, 40.0])


def test_conteo_par(valores_par):
    assert stats.conteo(valores_par) == 4


def test_mediana_par_es_promedio_de_los_dos_centrales(valores_par):
    assert stats.mediana(valores_par) == 25.0


def test_desviacion_estandar_par(valores_par):
    assert stats.desviacion_estandar(valores_par) == pytest.approx(math.sqrt(125))


# --------------------------------------------------------------------------- #
# Un solo elemento: desviación estándar debe ser 0, no NaN ni error.
# --------------------------------------------------------------------------- #

def test_un_solo_elemento():
    valores = pd.Series([42.0])
    assert stats.conteo(valores) == 1
    assert stats.suma(valores) == 42.0
    assert stats.promedio(valores) == 42.0
    assert stats.minimo(valores) == 42.0
    assert stats.maximo(valores) == 42.0
    assert stats.mediana(valores) == 42.0
    assert stats.desviacion_estandar(valores) == 0.0


# --------------------------------------------------------------------------- #
# Conjunto vacío: conteo y suma están definidos (0); el resto debe lanzar
# SinDatosError, para que el futuro exception handler devuelva un 500 "IE".
# --------------------------------------------------------------------------- #

@pytest.fixture
def valores_vacios():
    return pd.Series([], dtype=float)


def test_conteo_vacio_es_cero(valores_vacios):
    assert stats.conteo(valores_vacios) == 0


def test_suma_vacia_es_cero(valores_vacios):
    assert stats.suma(valores_vacios) == 0.0


@pytest.mark.parametrize(
    "funcion",
    [stats.promedio, stats.minimo, stats.maximo, stats.mediana, stats.desviacion_estandar],
)
def test_metricas_indefinidas_lanzan_sin_datos_error(valores_vacios, funcion):
    with pytest.raises(stats.SinDatosError):
        funcion(valores_vacios)


def test_calcular_estadisticas_vacio_lanza_sin_datos_error(valores_vacios):
    with pytest.raises(stats.SinDatosError):
        stats.calcular_estadisticas(valores_vacios)


# --------------------------------------------------------------------------- #
# Valores negativos y con decimales, para no asumir solo montos positivos.
# --------------------------------------------------------------------------- #

def test_valores_negativos_y_decimales():
    valores = pd.Series([-10.5, 0.0, 10.5, 20.25])
    assert stats.suma(valores) == pytest.approx(20.25)
    assert stats.conteo(valores) == 4
    assert stats.minimo(valores) == -10.5
    assert stats.maximo(valores) == 20.25
    assert stats.mediana(valores) == pytest.approx((0.0 + 10.5) / 2)
