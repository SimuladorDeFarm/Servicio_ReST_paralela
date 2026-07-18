"""Prueba automatizada de extremo a extremo contra una API en ejecución.

Lee los casos de `datos.json` (request + respuesta esperada, calculados
contra el CSV real) y los ejecuta contra una instancia real de la API vía
HTTP, comparando la respuesta obtenida con la esperada.

Requiere que la API ya esté corriendo (con el CSV real cargado):

    uvicorn app.main:app &
    python -m scripts.probar_api

Uso:
    python -m scripts.probar_api [--base-url http://127.0.0.1:8000] [--datos datos.json]
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict

import httpx

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def _valores_aproximadamente_iguales(esperado: Any, obtenido: Any) -> bool:
    if isinstance(esperado, float) or isinstance(obtenido, float):
        try:
            return math.isclose(float(esperado), float(obtenido), rel_tol=1e-9, abs_tol=1e-6)
        except (TypeError, ValueError):
            return False
    return esperado == obtenido


def _ejecutar_caso(client: httpx.Client, caso: Dict[str, Any]) -> str:
    """Ejecuta un caso y devuelve None si pasó, o un string con el motivo de la falla."""
    metodo = caso["metodo"]
    if metodo == "GET":
        resp = client.get("/v1/estadisticas/ventas", params=caso.get("query_params", {}))
    else:
        resp = client.post("/v1/estadisticas/ventas", json=caso.get("body", {}))

    status_esperado = caso["status_esperado"]
    if resp.status_code != status_esperado:
        return f"status {resp.status_code}, se esperaba {status_esperado} (body: {resp.text[:200]})"

    body = resp.json()

    if "error_code_esperado" in caso:
        if body.get("errorCode") != caso["error_code_esperado"]:
            return f"errorCode '{body.get('errorCode')}', se esperaba '{caso['error_code_esperado']}'"
        campos_error = {
            "detail", "instance", "status", "title", "type",
            "timestamp", "errorCode", "errorLabel", "method",
        }
        if set(body.keys()) != campos_error:
            return f"campos de error inesperados: {sorted(body.keys())}"
        return None

    esperado = caso["respuesta_esperada"]
    for campo, valor_esperado in esperado.items():
        valor_obtenido = body.get(campo)
        if not _valores_aproximadamente_iguales(valor_esperado, valor_obtenido):
            return f"campo '{campo}': se obtuvo {valor_obtenido}, se esperaba {valor_esperado}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--datos", default=str(RAIZ_PROYECTO / "datos.json"))
    args = parser.parse_args()

    datos = json.loads(Path(args.datos).read_text(encoding="utf-8"))
    casos = datos["casos"]

    ok = 0
    fallidos = []
    omitidos = []
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        for caso in casos:
            nombre = caso["nombre"]

            if caso.get("_pendiente_recalcular"):
                print(f"[SKIP] {nombre}: valores pendientes de recalcular")
                omitidos.append(nombre)
                continue

            try:
                motivo_falla = _ejecutar_caso(client, caso)
            except httpx.ConnectError:
                print(f"No se pudo conectar a {args.base_url}. ¿Está la API corriendo?")
                sys.exit(2)

            if motivo_falla is None:
                print(f"[OK]   {nombre}")
                ok += 1
            else:
                print(f"[FAIL] {nombre}: {motivo_falla}")
                fallidos.append(nombre)

    total_ejecutados = len(casos) - len(omitidos)
    print(f"\n{ok}/{total_ejecutados} casos OK")
    if omitidos:
        print(f"Omitidos (pendientes de recalcular): {', '.join(omitidos)}")
    if fallidos:
        print(f"Fallaron: {', '.join(fallidos)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
