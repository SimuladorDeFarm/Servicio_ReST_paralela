# Api Computacion Paralela

Servicio REST de estadísticas de ventas (Cruz Morada) con carga paralela de CSV.

## Requisitos

- Python 3.8+

## Instalación

```bash
git clone https://github.com/SimuladorDeFarm/Servicio_ReST_paralela
cd Servicio_ReST_paralela

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Descargar el CSV de ventas

**Opción 1** — Script automático:
```bash
python -m scripts.descargar_csv
```

**Opción 2** — Descarga manual (si el script falla por permisos de Drive):
1. Descargar desde: https://drive.google.com/file/d/15jLBlJ9eMQSoHsoCMnFWBGopr98FIHlK/view
2. Crear la carpeta `data/` en la raíz del proyecto si no existe.
3. Guardar el archivo como `data/ventas_completas.csv`.

El CSV pesa ~635 MB. La API no arranca sin él.

## Ejecución

Desde la **raíz del proyecto** (no desde dentro de `app/`):

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Ejecución con HTTPS

```bash
# Generar certificados autofirmados (una sola vez):
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

# Arrancar con HTTPS:
uvicorn app.main:app --ssl-keyfile key.pem --ssl-certfile cert.pem
```

La app carga el CSV automáticamente al iniciar (carga desatendida) e imprime
en consola el progreso, tiempo de carga y workers usados. Una vez lista, la
API queda disponible.

### Variables de entorno opcionales

| Variable | Default | Descripción |
|---|---|---|
| `VENTAS_CSV_PATH` | `data/ventas_completas.csv` | Ruta al CSV a cargar |
| `VENTAS_N_WORKERS` | Nº de CPUs disponibles | Procesos worker para la carga paralela |
| `VENTAS_CHUNKS_PER_WORKER` | `2` | Chunks por worker |
| `API_KEY` | (vacía = sin auth) | Si se define, toda petición debe incluir `X-API-Key` |
| `CORS_ORIGINS` | `*` | Orígenes permitidos para CORS, separados por coma |

## Autenticación

Si se configura la variable `API_KEY`, toda petición debe incluir el header
`X-API-Key`:

```bash
curl -H "X-API-Key: mi-clave" "https://127.0.0.1:8000/v1/estadisticas/ventas?CANAL=POS"
```

Si `API_KEY` no está definida, la API funciona sin autenticación.

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
| GENERO | `GENERO` | `No especificado`, `Masculino`, `Femenino`, `Otro` |
| EDAD | `EDAD` | entero |
| CANAL | `CANAL` | `POS`, `WEB`, `APP`, `CCT`, `APR`, `WPR` |
| CODIGO_PRODUCTO | `CODIGO_PRODUCTO` | entero (SKU) |
| ID_PERSONA | `ID_PERSONA` | UUID del cliente |
| LOCAL | `LOCAL` | entero |
| FECHA_DESDE | `FECHA_DESDE` | fecha ISO-8601 |
| FECHA_HASTA | `FECHA_HASTA` | fecha ISO-8601 (incluye todo el día) |

Documentación interactiva (Swagger) en `/docs` una vez que la app está
corriendo.

### Ejemplo GET

```bash
curl "http://127.0.0.1:8000/v1/estadisticas/ventas?GENERO=Femenino&CANAL=POS"
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

El POST requiere al menos un filtro en la lista `consultas`. Un body vacío o
con `consultas` vacía devuelve 400.

### Ejemplo de error (400)

Un filtro con valor inválido (ej. `CANAL=FAX`) responde 400:

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

### Códigos de error

| Código | Cuándo | `errorCode` |
|---|---|---|
| 400 | Filtro inválido, lista vacía, rango invertido, UUID inválido | `VF` |
| 401 | API Key inválida o ausente (si `API_KEY` configurada) | `NA` |
| 404 | Ruta no existente | `NE` |
| 405 | Método HTTP no soportado (PUT, DELETE, etc.) | `MN` |
| 429 | Rate limit excedido (60 req/min por IP) | `DL` |
| 500 | Filtros válidos pero sin filas coincidentes | `IE` |

## Seguridad

- **HTTPS**: certificados SSL configurables en uvicorn.
- **API Key**: autenticación opcional por header `X-API-Key`.
- **CORS**: solo GET y POST, headers controlados.
- **Rate limiting**: 60 req/min por IP (slowapi).
- **Minimización de datos**: columnas con datos personales eliminadas tras la carga.

## Pruebas

### Pruebas unitarias e integración (pytest)

```bash
source .venv/bin/activate
pytest tests/ -v
```

44 tests que cubren: filtros en mayúsculas, FECHA_HASTA día completo,
validación UUID, rango de fechas invertido, consultas vacías, campos
desconocidos, errores 404/405, autenticación API Key, minimización de datos.

Corren contra una fixture en memoria (sin CSV externo) — son rápidas y
deterministas.

### Prueba E2E (contra la API real)

Con la API corriendo y cargada con el CSV completo:

```bash
python -m scripts.probar_api
```

Compara cada caso de `datos.json` contra la respuesta real y reporta
`OK`/`FAIL` por caso.
