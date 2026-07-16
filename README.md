# api_paralela

Servicio REST de estadísticas de ventas (Cruz Morada) con carga paralela de CSV.

## Requisitos

- Python 3.8+
- El CSV de ventas en `data/ventas_completas.csv`

## Instalación

```bash
git clone <url-del-repo>
cd api_paralela

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Ejecución

Desde la **raíz del proyecto** (no desde dentro de `app/`):

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

La app carga el CSV automáticamente al iniciar (carga desatendida) e imprime
en consola el progreso, tiempo de carga y workers usados. Una vez lista, la
API queda disponible en `http://127.0.0.1:8000`.

### Variables de entorno opcionales

| Variable | Default | Descripción |
|---|---|---|
| `VENTAS_CSV_PATH` | `data/ventas_completas.csv` | Ruta al CSV a cargar |
| `VENTAS_N_WORKERS` | Nº de CPUs disponibles | Procesos worker para la carga paralela |
| `VENTAS_CHUNKS_PER_WORKER` | `2` | Chunks por worker |

Ejemplo:

```bash
VENTAS_CSV_PATH=tests/fixtures/ventas_prueba.csv uvicorn app.main:app --reload
```

## Endpoint

```
GET  /v1/estadisticas/ventas
POST /v1/estadisticas/ventas
```

Ambos aceptan los mismos filtros (combinados con AND) y devuelven la misma
respuesta: `GET` los recibe como query params opcionales, `POST` como una
lista `consultas` en el body.

| Filtro | Query param (GET) | Tipo |
|---|---|---|
| GENERO | `genero` | `No especificado`, `Masculino`, `Femenino`, `Otro` |
| EDAD | `edad` | entero |
| CANAL | `canal` | `POS`, `WEB`, `APP`, `CCT`, `APR`, `WPR` |
| CODIGO_PRODUCTO | `codigo_producto` | entero (SKU) |
| ID_PERSONA | `id_persona` | UUID del cliente |
| LOCAL | `local` | entero |
| FECHA_DESDE | `fecha_desde` | fecha ISO-8601 |
| FECHA_HASTA | `fecha_hasta` | fecha ISO-8601 |

Documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs` una vez
que la app está corriendo.

### Ejemplo GET

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?genero=Femenino&canal=POS"
```

```json
{
  "suma": 20649356290.0,
  "conteo": 2086258,
  "promedio": 9897.79609712701,
  "minimo": 15.0,
  "maximo": 226475.0,
  "mediana": 7476.0,
  "desviacion_estandar": 14565.86678562017
}
```

### Ejemplo POST

```bash
curl -X POST http://127.0.0.1:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{
        "consultas": [
          {"consulta": "CANAL", "valor": "POS"},
          {"consulta": "GENERO", "valor": "Masculino"}
        ]
      }'
```

```json
{
  "suma": 11002764448.0,
  "conteo": 1033169,
  "promedio": 10649.530181412722,
  "minimo": 16.0,
  "maximo": 226476.0,
  "mediana": 7872.0,
  "desviacion_estandar": 14317.090578047004
}
```

`consultas` puede venir vacía (o el body vacío `{}`): en ese caso se
devuelven las estadísticas sobre el total de ventas, sin filtrar.

### Ejemplo de error (400 y 500)

Un filtro con valor inválido (ej. `canal=FAX`, fuera de los canales
soportados) responde 400:

```json
{
  "detail": "CANAL debe ser uno de ['APP', 'APR', 'CCT', 'POS', 'WEB', 'WPR'], se recibió 'FAX'",
  "instance": "/v1/estadisticas/ventas",
  "status": 400,
  "title": "Bad Request",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
  "timestamp": "2026-07-16T22:18:41.709656000Z",
  "errorCode": "VF",
  "errorLabel": "Validación Fallida",
  "method": "GET"
}
```

Un filtro que no encuentra ninguna fila (las métricas quedan indefinidas)
responde 500 con el mismo formato, `errorCode: "IE"`.

## Pruebas

### Pruebas unitarias e integración (pytest)

```bash
source .venv/bin/activate
pytest tests/ -v
```

Corren contra una fixture pequeña (`tests/fixtures/ventas_prueba.csv`), no
contra el CSV real — son rápidas y no dependen de tener el archivo de 635 MB.

### Prueba automatizada de extremo a extremo (contra la API real)

`datos.json` (raíz del proyecto) contiene casos de prueba — request +
respuesta esperada — calculados contra el CSV real completo. Con la API
corriendo (cargada con `data/ventas_completas.csv`), se pueden validar todos
automáticamente:

```bash
# en una terminal:
uvicorn app.main:app

# en otra terminal:
python -m scripts.probar_api
```

Compara cada caso de `datos.json` contra la respuesta real de la API y
reporta un resumen (`OK`/`FAIL` por caso). Devuelve código de salida 1 si
algún caso falla, útil para automatizar la verificación tras cualquier
cambio.
