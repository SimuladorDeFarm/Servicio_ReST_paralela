# Cálculo puro de las 7 métricas estadísticas (suma, conteo, promedio, minimo, maximo,
# mediana, desviacion_estandar). Funciones sin estado global, operan sobre cualquier pd.Series.

from typing import Dict

import numpy as np
import pandas as pd


# Conjunto vacío: promedio/minimo/maximo/mediana/desviacion_estandar quedan indefinidos -> 500 (IE).
class SinDatosError(ValueError):
    pass


# Número de registros del subconjunto. Válido incluso si está vacío (0).
def conteo(valores: pd.Series) -> int:
    return int(len(valores))


# Suma de los valores. 0.0 si el subconjunto está vacío.
def suma(valores: pd.Series) -> float:
    return float(valores.sum())


# suma / conteo.
def promedio(valores: pd.Series) -> float:
    n = conteo(valores)
    if n == 0:
        raise SinDatosError("no hay datos para calcular el promedio")
    return suma(valores) / n


# Valor mínimo del subconjunto.
def minimo(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular el mínimo")
    return float(valores.min())


# Valor máximo del subconjunto.
def maximo(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular el máximo")
    return float(valores.max())


# Valor central; promedio de los 2 centrales si el conteo es par.
def mediana(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular la mediana")
    ordenados = np.sort(np.asarray(valores, dtype=float))
    n = len(ordenados)
    mitad = n // 2
    if n % 2 == 0:
        return float((ordenados[mitad - 1] + ordenados[mitad]) / 2)
    return float(ordenados[mitad])


# Raíz cuadrada de la varianza poblacional (ddof=0).
def desviacion_estandar(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular la desviación estándar")
    varianza = float(np.asarray(valores, dtype=float).var(ddof=0))
    return float(np.sqrt(varianza))


# Calcula las 7 métricas y las devuelve en un dict con las claves exactas de la respuesta.
def calcular_estadisticas(valores: pd.Series) -> Dict[str, float]:
    return {
        "suma": suma(valores),
        "conteo": conteo(valores),
        "promedio": promedio(valores),
        "minimo": minimo(valores),
        "maximo": maximo(valores),
        "mediana": mediana(valores),
        "desviacion_estandar": desviacion_estandar(valores),
    }
