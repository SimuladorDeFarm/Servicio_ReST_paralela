"""Cálculo puro de las métricas estadísticas de ventas (CLAUDE.md §7, §9).

Cada función es pura (sin estado global, sin I/O) y opera sobre una
`pd.Series` numérica — típicamente la columna `MONTO_APLICADO` del
DataFrame ya filtrado por `filters`. Esto permite testear cada métrica de
forma aislada, sin pasar por el CSV real ni por `data_store`.

Fórmulas:
- promedio = suma / conteo
- mediana: valor central (si el conteo es par, promedio de los 2 centrales)
- desviación estándar: raíz cuadrada de la varianza poblacional (ddof=0)
"""

from typing import Dict

import numpy as np
import pandas as pd


class SinDatosError(ValueError):
    """El subconjunto está vacío.

    Las métricas que dependen del conteo (promedio, mínimo, máximo, mediana,
    desviación estándar) no están matemáticamente definidas sobre un conjunto
    vacío. El handler de errores (módulo `errors`, aún no implementado)
    traduce esta excepción a un 500 con `errorCode: "IE"`, como especifica
    el enunciado ("error de cálculo interno").
    """


def conteo(valores: pd.Series) -> int:
    """Número de registros del subconjunto. Válido incluso si está vacío (0)."""
    return int(len(valores))


def suma(valores: pd.Series) -> float:
    """Suma de los valores. 0.0 si el subconjunto está vacío."""
    return float(valores.sum())


def promedio(valores: pd.Series) -> float:
    """suma / conteo."""
    n = conteo(valores)
    if n == 0:
        raise SinDatosError("no hay datos para calcular el promedio")
    return suma(valores) / n


def minimo(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular el mínimo")
    return float(valores.min())


def maximo(valores: pd.Series) -> float:
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular el máximo")
    return float(valores.max())


def mediana(valores: pd.Series) -> float:
    """Valor central; promedio de los 2 centrales si el conteo es par."""
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular la mediana")
    ordenados = np.sort(np.asarray(valores, dtype=float))
    n = len(ordenados)
    mitad = n // 2
    if n % 2 == 0:
        return float((ordenados[mitad - 1] + ordenados[mitad]) / 2)
    return float(ordenados[mitad])


def desviacion_estandar(valores: pd.Series) -> float:
    """Raíz cuadrada de la varianza poblacional (ddof=0)."""
    if conteo(valores) == 0:
        raise SinDatosError("no hay datos para calcular la desviación estándar")
    varianza = float(np.asarray(valores, dtype=float).var(ddof=0))
    return float(np.sqrt(varianza))


def calcular_estadisticas(valores: pd.Series) -> Dict[str, float]:
    """Calcula las 7 métricas del enunciado sobre `valores`.

    Devuelve un dict con las claves exactas de la respuesta (CLAUDE.md §7):
    suma, conteo, promedio, minimo, maximo, mediana, desviacion_estandar.
    Lanza `SinDatosError` si `valores` está vacío (ver la excepción).
    """
    return {
        "suma": suma(valores),
        "conteo": conteo(valores),
        "promedio": promedio(valores),
        "minimo": minimo(valores),
        "maximo": maximo(valores),
        "mediana": mediana(valores),
        "desviacion_estandar": desviacion_estandar(valores),
    }
