"""Pruebas unitarias del armado del cuerpo de error (`app.errors`)."""

import re

from starlette.requests import Request

from app import errors


def _fake_request(method: str = "GET", path: str = "/v1/estadisticas/ventas") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def test_timestamp_formato_iso_con_z():
    ts = errors._timestamp()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{9}Z$", ts)


def test_cuerpo_error_400():
    request = _fake_request(method="POST")
    cuerpo = errors._cuerpo_error(
        request=request,
        status_code=400,
        detail="mensaje de prueba",
        error_code="VF",
        error_label="Validación Fallida",
    )
    assert cuerpo == {
        "detail": "mensaje de prueba",
        "instance": "/v1/estadisticas/ventas",
        "status": 400,
        "title": "Bad Request",
        "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
        "timestamp": cuerpo["timestamp"],
        "errorCode": "VF",
        "errorLabel": "Validación Fallida",
        "method": "POST",
    }


def test_cuerpo_error_500():
    request = _fake_request(method="GET")
    cuerpo = errors._cuerpo_error(
        request=request,
        status_code=500,
        detail="fallo interno",
        error_code="IE",
        error_label="Error Interno",
    )
    assert cuerpo["status"] == 500
    assert cuerpo["title"] == "Internal Server Error"
    assert cuerpo["type"] == "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500"
    assert cuerpo["errorCode"] == "IE"
    assert cuerpo["method"] == "GET"
