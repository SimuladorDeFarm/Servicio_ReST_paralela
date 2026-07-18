"""Pruebas del data_loader: correctitud del parseo, tipado y equivalencia
entre la carga secuencial y la paralela (chunking por bytes).
"""

import os
import random
from pathlib import Path

import pandas as pd
import pytest

from app import data_loader

FIXTURE = Path(__file__).parent / "fixtures" / "ventas_prueba.csv"


# --------------------------------------------------------------------------- #
# Fixture pequeña con valores conocidos
# --------------------------------------------------------------------------- #

def test_fixture_valores_conocidos():
    df = data_loader.load_csv_sequential(str(FIXTURE))

    assert len(df) == 5
    assert list(df.columns[:3]) == ["FECHA", "CANAL", "SKU"]

    # EDAD al momento de la venta (años cumplidos).
    assert df["EDAD"].tolist() == [33, 32, 22, 38, 28]

    # GENERO normalizado a etiquetas del enunciado (9 -> No especificado).
    assert df["GENERO"].tolist() == [
        "Masculino",
        "Femenino",
        "No especificado",
        "Masculino",
        "Femenino",
    ]

    # Métricas base sobre MONTO_APLICADO.
    assert df["MONTO_APLICADO"].sum() == 7750.0

    # Columnas canónicas (con guion bajo) presentes.
    for col in [
        "PORCENTAJE_DESCUENTO",
        "MONTO_APLICADO",
        "CODIGO_CLIENTE",
        "RUN_CLIENTE",
        "FECHA_NACIMIENTO",
    ]:
        assert col in df.columns


def test_fixture_tipos():
    df = data_loader.load_csv_sequential(str(FIXTURE))
    assert pd.api.types.is_datetime64_any_dtype(df["FECHA"])
    assert pd.api.types.is_datetime64_any_dtype(df["FECHA_NACIMIENTO"])
    assert isinstance(df["CANAL"].dtype, pd.CategoricalDtype)
    assert isinstance(df["GENERO"].dtype, pd.CategoricalDtype)
    assert isinstance(df["LOCAL"].dtype, pd.CategoricalDtype)
    assert df["SKU"].dtype == "int32"
    assert df["MONTO_APLICADO"].dtype == "float64"
    assert str(df["EDAD"].dtype) == "Int16"


def test_paralelo_igual_secuencial_fixture():
    seq = data_loader.load_csv_sequential(str(FIXTURE))
    par = data_loader.load_csv(str(FIXTURE), n_workers=4)
    pd.testing.assert_frame_equal(seq, par)


# --------------------------------------------------------------------------- #
# Archivo mayor generado al vuelo: fuerza múltiples chunks y fronteras reales
# --------------------------------------------------------------------------- #

def _generar_csv(path: Path, n_filas: int) -> None:
    rng = random.Random(42)
    canales = ["POS", "WEB", "APP", "CCT", "APR", "WPR"]
    header = (
        '"FECHA";"CANAL";"SKU";"PRODUCTO";"UNIDADES";"PORCENTAJE DESCUENTO";'
        '"MONTO APLICADO";"BOLETA";"LOCAL";"CODIGO CLIENTE";"RUN CLIENTE";'
        '"NOMBRES";"APELLIDOS";"FECHA NACIMIENTO";"GENERO"\n'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for i in range(n_filas):
            mes = rng.randint(1, 12)
            dia = rng.randint(1, 28)
            anio_nac = rng.randint(1950, 2005)
            fila = (
                f'"2023-{mes:02d}-{dia:02d}T{rng.randint(0,23):02d}:00:00";'
                f'"{rng.choice(canales)}";"{rng.randint(100, 999)}";'
                f'"PRODUCTO {i % 50}";"{rng.randint(1, 5)}";'
                f'"0.{rng.randint(0, 5)}000";"{rng.randint(500, 50000)}";'
                f'"{1000000 + i}";"{rng.randint(300, 600)}";'
                f'"{i:08d}-0000-4000-8000-000000000000";"{rng.randint(1,25)}.000.000-0";'
                f'"NOMBRE {i}";"APELLIDO {i}";'
                f'"{anio_nac}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}";'
                f'"{rng.choice([1, 2])}"\n'
            )
            f.write(fila)


def test_paralelo_igual_secuencial_grande(tmp_path):
    csv = tmp_path / "grande.csv"
    _generar_csv(csv, 20000)

    seq = data_loader.load_csv_sequential(str(csv))
    # 4 workers x 3 chunks = hasta 12 rangos -> ejercita el alineado de fronteras.
    par = data_loader.load_csv(str(csv), n_workers=4, chunks_per_worker=3)

    assert len(seq) == 20000
    assert len(par) == 20000
    pd.testing.assert_frame_equal(seq, par)


def test_particion_cubre_todas_las_filas(tmp_path):
    csv = tmp_path / "cobertura.csv"
    _generar_csv(csv, 5000)

    for n in [1, 2, 3, 7, 16]:
        df = data_loader.load_csv(str(csv), n_workers=n)
        assert len(df) == 5000, f"n_workers={n} perdió/duplicó filas"


def test_archivo_solo_cabecera(tmp_path):
    csv = tmp_path / "vacio.csv"
    csv.write_text(
        '"FECHA";"CANAL";"SKU";"PRODUCTO";"UNIDADES";"PORCENTAJE DESCUENTO";'
        '"MONTO APLICADO";"BOLETA";"LOCAL";"CODIGO CLIENTE";"RUN CLIENTE";'
        '"NOMBRES";"APELLIDOS";"FECHA NACIMIENTO";"GENERO"\n'
    )
    df = data_loader.load_csv(str(csv), n_workers=4)
    assert len(df) == 0
