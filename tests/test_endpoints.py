"""Pruebas de integración de GET/POST /v1/estadisticas/ventas.

Usa la fixture pequeña (5 filas, valores conocidos) en vez del CSV real,
apuntando `VENTAS_CSV_PATH` allí *antes* de importar `app.main` (los valores
de configuración se leen una sola vez, al importar el módulo).
"""

import os
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "ventas_prueba.csv"
os.environ["VENTAS_CSV_PATH"] = str(FIXTURE)
os.environ["VENTAS_N_WORKERS"] = "2"
os.environ["VENTAS_CHUNKS_PER_WORKER"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_get_sin_filtros_devuelve_totales(client):
    resp = client.get("/v1/estadisticas/ventas")
    assert resp.status_code == 200
    body = resp.json()
    assert body["conteo"] == 5
    assert body["suma"] == 7750.0


def test_get_con_filtro_genero(client):
    resp = client.get("/v1/estadisticas/ventas", params={"genero": "Masculino"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conteo"] == 2
    assert body["suma"] == 4000.0


def test_get_con_multiples_filtros(client):
    resp = client.get(
        "/v1/estadisticas/ventas",
        params={"genero": "Femenino", "canal": "WEB"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conteo"] == 1
    assert body["suma"] == 2500.0


def test_get_con_filtro_invalido_da_400(client):
    resp = client.get("/v1/estadisticas/ventas", params={"canal": "FAX"})
    assert resp.status_code == 400


def test_get_sin_coincidencias_da_500(client):
    resp = client.get("/v1/estadisticas/ventas", params={"local": "999999"})
    assert resp.status_code == 500


def test_get_query_param_tipo_incorrecto_da_400(client):
    """edad no convertible a int a nivel de FastAPI/Pydantic (antes de
    llegar a `filters`) también debe quedar en el formato 400/VF."""
    resp = client.get("/v1/estadisticas/ventas", params={"edad": "no-es-un-entero"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["errorCode"] == "VF"


def test_post_consultas_vacia_devuelve_totales(client):
    resp = client.post("/v1/estadisticas/ventas", json={"consultas": []})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conteo"] == 5
    assert body["suma"] == 7750.0


def test_post_sin_body_de_consultas_devuelve_totales(client):
    resp = client.post("/v1/estadisticas/ventas", json={})
    assert resp.status_code == 200
    assert resp.json()["conteo"] == 5


def test_post_con_consultas_combinadas(client):
    resp = client.post(
        "/v1/estadisticas/ventas",
        json={
            "consultas": [
                {"consulta": "GENERO", "valor": "Masculino"},
                {"consulta": "LOCAL", "valor": "371"},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conteo"] == 2
    assert body["suma"] == 4000.0


def test_post_valor_invalido_da_400(client):
    resp = client.post(
        "/v1/estadisticas/ventas",
        json={"consultas": [{"consulta": "EDAD", "valor": "no-es-un-entero"}]},
    )
    assert resp.status_code == 400


def test_post_clave_no_reconocida_da_400(client):
    """Clave de filtro no reconocida: Pydantic la rechaza (422 nativo), pero
    el handler de `errors` para RequestValidationError la reescribe a 400/VF."""
    resp = client.post(
        "/v1/estadisticas/ventas",
        json={"consultas": [{"consulta": "NO_EXISTE", "valor": "x"}]},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["errorCode"] == "VF"


def test_respuesta_incluye_las_7_metricas(client):
    resp = client.get("/v1/estadisticas/ventas")
    body = resp.json()
    for campo in [
        "suma", "conteo", "promedio", "minimo", "maximo",
        "mediana", "desviacion_estandar",
    ]:
        assert campo in body


# --------------------------------------------------------------------------- #
# Formato exacto de error (CLAUDE.md §7): mismos 9 campos en 400 y 500.
# --------------------------------------------------------------------------- #

_CAMPOS_ERROR_ESPERADOS = {
    "detail", "instance", "status", "title", "type",
    "timestamp", "errorCode", "errorLabel", "method",
}


def test_error_400_tiene_formato_exacto(client):
    resp = client.get("/v1/estadisticas/ventas", params={"canal": "FAX"})
    body = resp.json()

    assert set(body.keys()) == _CAMPOS_ERROR_ESPERADOS
    assert body["status"] == 400
    assert body["title"] == "Bad Request"
    assert body["type"] == "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400"
    assert body["errorCode"] == "VF"
    assert body["errorLabel"] == "Validación Fallida"
    assert body["instance"] == "/v1/estadisticas/ventas"
    assert body["method"] == "GET"
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["timestamp"].endswith("Z")


def test_error_500_tiene_formato_exacto(client):
    resp = client.post(
        "/v1/estadisticas/ventas",
        json={"consultas": [{"consulta": "LOCAL", "valor": "999999"}]},
    )
    body = resp.json()

    assert set(body.keys()) == _CAMPOS_ERROR_ESPERADOS
    assert body["status"] == 500
    assert body["title"] == "Internal Server Error"
    assert body["type"] == "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500"
    assert body["errorCode"] == "IE"
    assert body["errorLabel"] == "Error Interno"
    assert body["instance"] == "/v1/estadisticas/ventas"
    assert body["method"] == "POST"
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["timestamp"].endswith("Z")


def test_excepcion_no_prevista_tambien_da_500_con_formato_exacto(monkeypatch):
    """Red de seguridad: un error totalmente inesperado (no `FiltroInvalidoError`
    ni `SinDatosError`) también debe quedar en el formato del enunciado.

    Usa `raise_server_exceptions=False`: por defecto Starlette re-lanza en el
    TestClient cualquier excepción no manejada explícitamente por el llamador
    (para que las fallas reales no queden ocultas en los tests), incluso
    cuando ya existe un exception_handler registrado que la procesó.
    """
    from app import endpoints
    from app.main import app as app_real

    def _explota(*args, **kwargs):
        raise RuntimeError("boom inesperado")

    monkeypatch.setattr(endpoints.stats, "calcular_estadisticas", _explota)

    with TestClient(app_real, raise_server_exceptions=False) as client_sin_relanzar:
        resp = client_sin_relanzar.get("/v1/estadisticas/ventas")
    assert resp.status_code == 500
    body = resp.json()
    assert set(body.keys()) == _CAMPOS_ERROR_ESPERADOS
    assert body["errorCode"] == "IE"
