"""Pruebas Fase 4: seguridad (API Key, CORS, minimización de datos)."""
import os

import pandas as pd

from app import data_store

CAMPOS_ERROR = {"detail", "instance", "status", "title", "type", "timestamp", "errorCode", "errorLabel", "method"}


class TestAPIKey:
    """Paso 10: autenticación por API Key."""

    def test_sin_api_key_env_no_requiere_auth(self, client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "")
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "CANAL", "valor": "POS"}]
        })
        assert resp.status_code == 200

    def test_con_api_key_env_requiere_header(self, client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "mi-clave-secreta")
        resp = client.post("/v1/estadisticas/ventas", json={
            "consultas": [{"consulta": "CANAL", "valor": "POS"}]
        })
        assert resp.status_code == 401

    def test_con_api_key_correcta_ok(self, client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "mi-clave-secreta")
        resp = client.post(
            "/v1/estadisticas/ventas",
            json={"consultas": [{"consulta": "CANAL", "valor": "POS"}]},
            headers={"X-API-Key": "mi-clave-secreta"},
        )
        assert resp.status_code == 200

    def test_con_api_key_incorrecta_401(self, client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "mi-clave-secreta")
        resp = client.post(
            "/v1/estadisticas/ventas",
            json={"consultas": [{"consulta": "CANAL", "valor": "POS"}]},
            headers={"X-API-Key": "clave-equivocada"},
        )
        assert resp.status_code == 401

    def test_health_no_requiere_api_key(self, client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "mi-clave-secreta")
        resp = client.get("/health")
        assert resp.status_code == 200


class TestMinimizacionDatos:
    """Paso 13: columnas sensibles eliminadas del DataFrame."""

    def test_no_contiene_columnas_sensibles(self):
        df = data_store.get_ventas_df()
        columnas_sensibles = {"RUN_CLIENTE", "NOMBRES", "APELLIDOS", "FECHA_NACIMIENTO", "BOLETA"}
        presentes = columnas_sensibles & set(df.columns)
        assert not presentes, f"Columnas sensibles presentes: {presentes}"

    def test_contiene_columnas_necesarias(self):
        df = data_store.get_ventas_df()
        necesarias = {"FECHA", "CANAL", "SKU", "MONTO_APLICADO", "LOCAL", "CODIGO_CLIENTE", "GENERO", "EDAD"}
        faltantes = necesarias - set(df.columns)
        assert not faltantes, f"Columnas necesarias faltantes: {faltantes}"
