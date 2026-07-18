import os
from pathlib import Path

# `app.main` lee VENTAS_CSV_PATH una sola vez, al importarse (constante de
# módulo). Como conftest.py es lo primero que pytest importa, hay que fijar
# esto acá -- si no, el lifespan de cualquier TestClient carga el CSV real de
# ~634 MB en vez de la fixture pequeña. El DataFrame real de cada test de
# endpoint igual lo pisa `cargar_df_prueba` (autouse, más abajo); esto solo
# evita esa carga real innecesaria y lenta durante el arranque de la app.
os.environ.setdefault("VENTAS_CSV_PATH", str(Path(__file__).parent / "fixtures" / "ventas_prueba.csv"))
os.environ.setdefault("VENTAS_N_WORKERS", "2")
os.environ.setdefault("VENTAS_CHUNKS_PER_WORKER", "1")

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import data_store
from app.main import app


@pytest.fixture(autouse=True)
def cargar_df_prueba():
    df = pd.DataFrame({
        "FECHA": pd.to_datetime([
            "2024-05-01T10:00:00",
            "2024-05-15T14:30:00",
            "2024-05-31T23:00:00",
            "2024-06-01T08:00:00",
            "2024-06-15T12:00:00",
        ]),
        "CANAL": pd.Categorical(["POS", "WEB", "POS", "APP", "POS"]),
        "SKU": [100, 200, 100, 300, 200],
        "PRODUCTO": pd.Categorical(["Prod A", "Prod B", "Prod A", "Prod C", "Prod B"]),
        "UNIDADES": [1, 2, 1, 3, 1],
        "PORCENTAJE_DESCUENTO": [0.0, 0.1, 0.0, 0.15, 0.05],
        "MONTO_APLICADO": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
        "LOCAL": pd.Categorical([10, 20, 10, 30, 20]),
        "CODIGO_CLIENTE": [
            "550e8400-e29b-41d4-a716-446655440000",
            "660e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000",
            "770e8400-e29b-41d4-a716-446655440002",
            "660e8400-e29b-41d4-a716-446655440001",
        ],
        "GENERO": pd.Categorical(["Masculino", "Femenino", "Masculino", "Otro", "Femenino"]),
        "EDAD": pd.array([34, 38, 34, 24, 38], dtype="Int16"),
    })
    data_store.set_ventas_df(df)
    yield
    data_store._ventas_df = None


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)
