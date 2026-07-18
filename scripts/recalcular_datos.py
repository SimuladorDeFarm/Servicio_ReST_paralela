"""Recalcula los valores esperados de datos.json contra el CSV real.

Uso (con el CSV ya descargado en data/ventas_completas.csv):
    python -m scripts.recalcular_datos

Carga el CSV con el mismo pipeline que la API (data_loader), aplica los
filtros de cada caso de datos.json y recalcula las estadísticas. Actualiza
el archivo datos.json con los valores correctos y elimina el flag
_pendiente_recalcular.
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.data_loader import load_csv
from app.filters import aplicar_filtros
from app.schemas import ConsultaFiltro
from app.stats import calcular_estadisticas


def _params_a_consultas(params: dict) -> list[ConsultaFiltro]:
    mapping = {
        "GENERO": "GENERO",
        "EDAD": "EDAD",
        "CANAL": "CANAL",
        "CODIGO_PRODUCTO": "CODIGO_PRODUCTO",
        "ID_PERSONA": "ID_PERSONA",
        "LOCAL": "LOCAL",
        "FECHA_DESDE": "FECHA_DESDE",
        "FECHA_HASTA": "FECHA_HASTA",
    }
    consultas = []
    for clave, valor in params.items():
        tipo = mapping.get(clave, clave)
        consultas.append(ConsultaFiltro(consulta=tipo, valor=str(valor)))
    return consultas


def main() -> None:
    datos_path = RAIZ / "datos.json"
    csv_path = RAIZ / "data" / "ventas_completas.csv"

    if not csv_path.exists():
        print(f"CSV no encontrado en {csv_path}")
        print("Descárgalo primero: python -m scripts.descargar_csv")
        sys.exit(1)

    print("Cargando CSV...")
    df = load_csv(str(csv_path))
    print(f"  {len(df)} filas cargadas")

    datos = json.loads(datos_path.read_text(encoding="utf-8"))
    casos = datos["casos"]
    recalculados = 0

    for caso in casos:
        if caso.get("status_esperado") != 200:
            continue
        if "respuesta_esperada" not in caso:
            continue

        nombre = caso["nombre"]
        params = caso.get("query_params", {})
        body = caso.get("body", {})

        if caso["metodo"] == "GET":
            if not params:
                consultas = []
            else:
                consultas = _params_a_consultas(params)
        else:
            consultas_raw = body.get("consultas", [])
            consultas = [ConsultaFiltro(**c) for c in consultas_raw]

        if not consultas:
            sub = df
        else:
            sub = aplicar_filtros(df, consultas)

        stats = calcular_estadisticas(sub["MONTO_APLICADO"])

        anterior = caso["respuesta_esperada"]
        cambio = any(
            abs(stats[k] - anterior[k]) > 0.001
            for k in stats
            if k in anterior
        )

        if cambio:
            print(f"  [UPD] {nombre}:")
            for k in stats:
                if k in anterior and abs(stats[k] - anterior[k]) > 0.001:
                    print(f"        {k}: {anterior[k]} -> {stats[k]}")
            caso["respuesta_esperada"] = stats
            recalculados += 1
        else:
            print(f"  [OK]  {nombre}: sin cambios")

        if "_pendiente_recalcular" in caso:
            del caso["_pendiente_recalcular"]

    if "_nota_fecha_hasta" in datos:
        del datos["_nota_fecha_hasta"]

    datos_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{recalculados} caso(s) actualizados en datos.json")


if __name__ == "__main__":
    main()
