"""Pruebas Fase 1: correcciones críticas."""


class TestFiltrosGETMayusculas:
    """Paso 1: Los query params deben aceptar nombres en mayúsculas."""

    def test_genero_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?GENERO=Femenino")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_canal_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?CANAL=POS")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 3

    def test_edad_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?EDAD=34")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_local_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?LOCAL=10")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_codigo_producto_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?CODIGO_PRODUCTO=100")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_id_persona_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?ID_PERSONA=550e8400-e29b-41d4-a716-446655440000")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_fecha_desde_mayuscula(self, client):
        resp = client.get("/v1/estadisticas/ventas?FECHA_DESDE=2024-06-01")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_combinacion_mayusculas(self, client):
        resp = client.get("/v1/estadisticas/ventas?GENERO=Masculino&CANAL=POS")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_minusculas_se_ignoran(self, client):
        resp = client.get("/v1/estadisticas/ventas?genero=Femenino")
        assert resp.status_code == 200
        # minúsculas no son reconocidas por la pauta; se ignoran y devuelve totales
        assert resp.json()["conteo"] == 5


class TestFechaHastaDiaCompleto:
    """Paso 2: FECHA_HASTA sin hora debe incluir todo el día."""

    def test_fecha_hasta_incluye_dia_completo(self, client):
        resp = client.get("/v1/estadisticas/ventas?FECHA_HASTA=2024-05-31")
        assert resp.status_code == 200
        # Debe incluir la venta del 31 de mayo a las 23:00
        assert resp.json()["conteo"] == 3

    def test_fecha_hasta_con_hora_no_se_extiende(self, client):
        resp = client.get("/v1/estadisticas/ventas?FECHA_HASTA=2024-05-15T14:30:00")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_rango_mayo_completo(self, client):
        resp = client.get("/v1/estadisticas/ventas?FECHA_DESDE=2024-05-01&FECHA_HASTA=2024-05-31")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 3


class TestConsultasVacias400:
    """Paso 3: POST con consultas vacía o nula debe dar 400."""

    def test_consultas_lista_vacia(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={"consultas": []})
        assert resp.status_code == 400

    def test_body_sin_consultas(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={})
        assert resp.status_code == 400

    def test_body_vacio(self, client):
        resp = client.post("/v1/estadisticas/ventas", content=b"", headers={"Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_consultas_con_filtro_valido_ok(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "CANAL", "valor": "POS"}]
        })
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 3


class TestCamposDesconocidos400:
    """Paso 4: Campos extra en el body deben dar 400."""

    def test_campo_extra_en_body(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "CANAL", "valor": "POS"}],
            "extra_field": "valor",
        })
        assert resp.status_code == 400

    def test_campo_extra_en_filtro(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "CANAL", "valor": "POS", "extra": "x"}],
        })
        assert resp.status_code == 400

    def test_body_con_campo_equivocado(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "filtros": [{"consulta": "CANAL", "valor": "POS"}],
        })
        assert resp.status_code == 400

    def test_formato_error_tiene_9_campos(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [],
        })
        assert resp.status_code == 400
        body = resp.json()
        campos_esperados = {"detail", "instance", "status", "title", "type", "timestamp", "errorCode", "errorLabel", "method"}
        assert set(body.keys()) == campos_esperados
