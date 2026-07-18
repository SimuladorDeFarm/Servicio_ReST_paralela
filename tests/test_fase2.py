"""Pruebas Fase 2: validaciones faltantes."""


class TestIDPersonaUUID:
    """Paso 5: ID_PERSONA debe validar formato UUID."""

    def test_uuid_valido(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "ID_PERSONA", "valor": "550e8400-e29b-41d4-a716-446655440000"}]
        })
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_uuid_invalido_da_400(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "ID_PERSONA", "valor": "no-soy-uuid"}]
        })
        assert resp.status_code == 400
        assert resp.json()["errorCode"] == "VF"

    def test_uuid_numerico_da_400(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "ID_PERSONA", "valor": "12345"}]
        })
        assert resp.status_code == 400

    def test_uuid_vacio_da_400(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "ID_PERSONA", "valor": ""}]
        })
        assert resp.status_code == 400

    def test_uuid_valido_via_get(self, client):
        resp = client.get("/v1/estadisticas/ventas?ID_PERSONA=550e8400-e29b-41d4-a716-446655440000")
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2

    def test_uuid_invalido_via_get(self, client):
        resp = client.get("/v1/estadisticas/ventas?ID_PERSONA=hola")
        assert resp.status_code == 400


class TestFechaDesdeHastaInvertido:
    """Paso 6: FECHA_DESDE > FECHA_HASTA debe dar 400."""

    def test_rango_invertido_post(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [
                {"consulta": "FECHA_DESDE", "valor": "2025-12-31"},
                {"consulta": "FECHA_HASTA", "valor": "2024-01-01"},
            ]
        })
        assert resp.status_code == 400
        assert resp.json()["errorCode"] == "VF"
        assert "FECHA_DESDE" in resp.json()["detail"]

    def test_rango_invertido_get(self, client):
        resp = client.get("/v1/estadisticas/ventas?FECHA_DESDE=2025-12-31&FECHA_HASTA=2024-01-01")
        assert resp.status_code == 400

    def test_rango_normal_funciona(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [
                {"consulta": "FECHA_DESDE", "valor": "2024-05-01"},
                {"consulta": "FECHA_HASTA", "valor": "2024-05-31"},
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 3

    def test_mismo_dia_funciona(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [
                {"consulta": "FECHA_DESDE", "valor": "2024-05-15"},
                {"consulta": "FECHA_HASTA", "valor": "2024-05-15"},
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 1

    def test_solo_fecha_desde_sin_hasta(self, client):
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "FECHA_DESDE", "valor": "2024-06-01"}]
        })
        assert resp.status_code == 200
        assert resp.json()["conteo"] == 2
