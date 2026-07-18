"""Pruebas de los modelos Pydantic de request/response."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    ConsultaFiltro,
    ErrorResponse,
    EstadisticasVentasQueryParams,
    EstadisticasVentasRequest,
    EstadisticasVentasResponse,
    TipoConsulta,
)


def test_consulta_filtro_valida():
    c = ConsultaFiltro(consulta="GENERO", valor="Femenino")
    assert c.consulta == TipoConsulta.GENERO
    assert c.valor == "Femenino"


def test_consulta_filtro_clave_no_reconocida_lanza_error():
    with pytest.raises(ValidationError):
        ConsultaFiltro(consulta="NO_EXISTE", valor="x")


def test_request_sin_consultas_lanza_error():
    """`consultas` es requerido (sin default) en el body del POST."""
    with pytest.raises(ValidationError):
        EstadisticasVentasRequest()


def test_request_consultas_vacia_lanza_error():
    """Lista vacía también es inválida: debe traer al menos un filtro."""
    with pytest.raises(ValidationError):
        EstadisticasVentasRequest(consultas=[])


def test_request_con_multiples_consultas():
    req = EstadisticasVentasRequest(
        consultas=[
            {"consulta": "GENERO", "valor": "Femenino"},
            {"consulta": "EDAD", "valor": "31"},
            {"consulta": "CANAL", "valor": "POS"},
        ]
    )
    assert len(req.consultas) == 3
    assert req.consultas[1].consulta == TipoConsulta.EDAD


def test_query_params_todos_opcionales():
    q = EstadisticasVentasQueryParams()
    assert q.GENERO is None
    assert q.EDAD is None
    assert q.LOCAL is None


def test_query_params_tipos():
    q = EstadisticasVentasQueryParams(EDAD=31, LOCAL=371, GENERO="Femenino")
    assert q.EDAD == 31
    assert q.LOCAL == 371


def test_response_campos_completos():
    resp = EstadisticasVentasResponse(
        suma=1500.5,
        conteo=42,
        promedio=35.73,
        minimo=10.0,
        maximo=100.0,
        mediana=30.0,
        desviacion_estandar=25.4,
    )
    assert resp.conteo == 42
    assert resp.suma == 1500.5


def test_error_response_formato_exacto():
    err = ErrorResponse(
        detail="Descripción detallada del error",
        instance="/v1/estadisticas/ventas",
        status=400,
        title="Bad Request",
        type="https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
        timestamp="2026-06-30T20:44:49.201437123Z",
        errorCode="VF",
        errorLabel="Validación Fallida",
        method="POST",
    )
    assert err.status == 400
    assert err.errorCode == "VF"
