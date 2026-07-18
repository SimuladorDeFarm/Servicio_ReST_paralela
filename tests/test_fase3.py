"""Pruebas Fase 3: formato de errores 404 y 405 con 9 campos."""

CAMPOS_ERROR = {"detail", "instance", "status", "title", "type", "timestamp", "errorCode", "errorLabel", "method"}


class TestError404:
    """Paso 7: rutas inexistentes devuelven 404 con formato de 9 campos."""

    def test_ruta_inexistente_da_404(self, client):
        resp = client.get("/v1/estadisticas/otra_cosa")
        assert resp.status_code == 404

    def test_404_tiene_formato_completo(self, client):
        resp = client.get("/v1/estadisticas/otra_cosa")
        body = resp.json()
        assert set(body.keys()) == CAMPOS_ERROR
        assert body["status"] == 404
        assert body["errorCode"] == "NE"
        assert body["errorLabel"] == "No Encontrado"
        assert body["title"] == "Not Found"
        assert body["method"] == "GET"

    def test_404_post_ruta_inexistente(self, client):
        resp = client.post("/v1/ruta/falsa", json={})
        assert resp.status_code == 404
        assert resp.json()["errorCode"] == "NE"


class TestError405:
    """Paso 8: métodos no permitidos devuelven 405 con formato de 9 campos."""

    def test_put_da_405(self, client):
        resp = client.put("/v1/estadisticas/ventas", json={})
        assert resp.status_code == 405

    def test_delete_da_405(self, client):
        resp = client.delete("/v1/estadisticas/ventas")
        assert resp.status_code == 405

    def test_405_tiene_formato_completo(self, client):
        resp = client.put("/v1/estadisticas/ventas", json={})
        body = resp.json()
        assert set(body.keys()) == CAMPOS_ERROR
        assert body["status"] == 405
        assert body["errorCode"] == "MN"
        assert body["errorLabel"] == "Método No Permitido"
        assert body["title"] == "Method Not Allowed"
        assert body["method"] == "PUT"
