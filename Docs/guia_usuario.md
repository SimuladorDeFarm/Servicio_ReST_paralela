# Guía de usuario

Servicio REST que entrega estadísticas de ventas de Cruz Morada a partir de
un CSV consolidado (~635 MB), cargado automáticamente al iniciar la
aplicación.

## 1. ¿Qué hace el servicio?

Al arrancar, la aplicación carga y procesa el CSV completo de ventas en
memoria (en paralelo, sin intervención manual). Una vez cargado, expone un
único endpoint que responde con un **resumen estadístico** — suma, conteo,
promedio, mínimo, máximo, mediana y desviación estándar — calculado sobre el
**monto pagado (`MONTO_APLICADO`)** de las ventas que coincidan con los
filtros que se indiquen.

Los filtros (género, edad, canal, producto, cliente, local, rango de
fechas) **acotan qué ventas entran al cálculo**; no cambian qué se mide. Por
ejemplo, "EDAD=31" pide "las estadísticas de venta de clientes de 31 años",
no "el promedio de edad de los clientes".

## 2. Instalación y ejecución

```bash
git clone https://github.com/SimuladorDeFarm/Servicio_ReST_paralela
cd Servicio_ReST_paralela

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Descargar el CSV de ventas

```bash
python -m scripts.descargar_csv
```

### Ejecutar (siempre desde la raíz del proyecto)

```bash
uvicorn app.main:app --reload
```

### Ejecutar con HTTPS

```bash
# Generar certificados autofirmados (una sola vez):
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

# Arrancar con HTTPS:
uvicorn app.main:app --ssl-keyfile key.pem --ssl-certfile cert.pem
```

La consola muestra el progreso de la carga (workers usados, tiempo, filas
cargadas). Una vez que dice "carga completa", la API está lista.

### Configuración opcional (variables de entorno)

| Variable | Default | Para qué sirve |
|---|---|---|
| `VENTAS_CSV_PATH` | `data/ventas_completas.csv` | Cambiar el CSV a cargar |
| `VENTAS_N_WORKERS` | Nº de CPUs del equipo | Cuántos procesos usar en la carga paralela |
| `VENTAS_CHUNKS_PER_WORKER` | `2` | Cuántos trozos de archivo procesa cada worker |
| `API_KEY` | (vacía = sin auth) | Si se define, toda petición debe incluir el header `X-API-Key` |
| `CORS_ORIGINS` | `*` | Orígenes permitidos para CORS, separados por coma |

## 3. Autenticación

Si se configura la variable `API_KEY`, toda petición al endpoint debe incluir
el header `X-API-Key`:

```bash
curl -H "X-API-Key: mi-clave" "https://127.0.0.1:8000/v1/estadisticas/ventas?CANAL=POS"
```

Si `API_KEY` no está definida, la API funciona sin autenticación.

## 4. El endpoint

```
GET  /v1/estadisticas/ventas
POST /v1/estadisticas/ventas
```

Ambos métodos aceptan los mismos filtros y devuelven la misma respuesta.
`GET` los recibe como parámetros en la URL (todos opcionales); `POST` los
recibe como una lista `consultas` en el body JSON. Se puede combinar
cualquier cantidad de filtros (se aplican todos a la vez, tipo "Y").

**Nota:** el POST requiere al menos un filtro en la lista `consultas`.

### Filtros soportados

| Filtro | Nombre en GET | Tipo / valores válidos |
|---|---|---|
| Género | `GENERO` | `No especificado`, `Masculino`, `Femenino`, `Otro` |
| Edad | `EDAD` | número entero |
| Canal de venta | `CANAL` | `POS`, `WEB`, `APP`, `CCT`, `APR`, `WPR` |
| Código de producto | `CODIGO_PRODUCTO` | número entero (SKU) |
| ID del cliente | `ID_PERSONA` | UUID válido |
| Local | `LOCAL` | número entero |
| Fecha desde | `FECHA_DESDE` | fecha `AAAA-MM-DD` (o ISO-8601 completo) |
| Fecha hasta | `FECHA_HASTA` | fecha `AAAA-MM-DD` (incluye todo el día) |

### Documentación interactiva (Swagger)

Con la app corriendo, abrir `http://127.0.0.1:8000/docs` en el navegador:
permite probar ambos métodos desde el navegador, ver los modelos de datos y
descargar la especificación OpenAPI.

## 5. Ejemplos

### GET con filtros combinados

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

### POST con body JSON

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

### Significado de cada campo de la respuesta

| Campo | Significado |
|---|---|
| `suma` | Total de `MONTO_APLICADO` de las ventas filtradas |
| `conteo` | Cantidad de ventas que coinciden con el filtro |
| `promedio` | `suma / conteo` |
| `minimo` / `maximo` | Venta más baja / más alta del subconjunto |
| `mediana` | Valor central (si el conteo es par, promedio de los 2 centrales) |
| `desviacion_estandar` | Qué tan dispersos están los montos respecto al promedio |

## 6. Errores

Todo error responde con un formato JSON consistente de 9 campos:

```json
{
  "detail": "descripción legible del problema",
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

| Código | Cuándo ocurre | `errorCode` |
|---|---|---|
| **400** | Filtro con clave no reconocida, valor no convertible, lista vacía, rango de fechas invertido, ID_PERSONA no UUID | `VF` (Validación Fallida) |
| **401** | API Key inválida o no proporcionada (si `API_KEY` está configurada) | `NA` (No Autorizado) |
| **404** | Ruta que no existe | `NE` (No Encontrado) |
| **405** | Método HTTP no soportado (ej. PUT, DELETE) | `MN` (Método No Permitido) |
| **429** | Demasiadas solicitudes (rate limit excedido) | `DL` (Demasiadas Solicitudes) |
| **500** | Filtros válidos pero sin filas coincidentes — métricas indefinidas | `IE` (Error Interno) |

## 7. Rate limiting

La API limita a 60 peticiones por minuto por IP. Si se excede, responde 429.

## 8. Seguridad

- **HTTPS**: soportado configurando certificados SSL en uvicorn.
- **API Key**: autenticación opcional por header `X-API-Key`.
- **CORS**: configuración restrictiva (solo GET y POST, headers controlados).
- **Minimización de datos**: las columnas con datos personales (RUT, nombres, apellidos, fecha de nacimiento) se eliminan del DataFrame en memoria tras la carga.
- **Rate limiting**: 60 req/min por IP para prevenir abuso.
