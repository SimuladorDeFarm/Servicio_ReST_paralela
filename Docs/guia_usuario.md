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

Ejecutar (siempre desde la raíz del proyecto, no desde dentro de `app/`):

```bash
uvicorn app.main:app --reload
```

La consola muestra el progreso de la carga (workers usados, tiempo, filas
cargadas). Una vez que dice "carga completa", la API está lista en
`http://127.0.0.1:8000`.

### Configuración opcional (variables de entorno)

| Variable | Default | Para qué sirve |
|---|---|---|
| `VENTAS_CSV_PATH` | `data/ventas_completas.csv` | Cambiar el CSV a cargar |
| `VENTAS_N_WORKERS` | Nº de CPUs del equipo | Cuántos procesos usar en la carga paralela |
| `VENTAS_CHUNKS_PER_WORKER` | `2` | Cuántos trozos de archivo procesa cada worker |

## 3. El endpoint

```
GET  /v1/estadisticas/ventas
POST /v1/estadisticas/ventas
```

Ambos métodos aceptan los mismos filtros y devuelven la misma respuesta.
`GET` los recibe como parámetros en la URL (todos opcionales); `POST` los
recibe como una lista `consultas` en el body JSON. Se puede combinar
cualquier cantidad de filtros (se aplican todos a la vez, tipo "Y").

### Filtros soportados

| Filtro | Nombre en GET | Tipo / valores válidos |
|---|---|---|
| Género | `genero` | `No especificado`, `Masculino`, `Femenino`, `Otro` |
| Edad | `edad` | número entero |
| Canal de venta | `canal` | `POS`, `WEB`, `APP`, `CCT`, `APR`, `WPR` |
| Código de producto | `codigo_producto` | número entero (SKU) |
| ID del cliente | `id_persona` | UUID |
| Local | `local` | número entero |
| Fecha desde | `fecha_desde` | fecha `AAAA-MM-DD` (o ISO-8601 completo) |
| Fecha hasta | `fecha_hasta` | fecha `AAAA-MM-DD` (o ISO-8601 completo) |

Si no se envía ningún filtro (GET sin parámetros, o POST con `consultas`
vacía o body vacío `{}`), la respuesta son las estadísticas sobre **todas**
las ventas, sin restringir.

### Documentación interactiva (Swagger)

Con la app corriendo, abrir `http://127.0.0.1:8000/docs` en el navegador:
permite probar ambos métodos desde el navegador, ver los modelos de datos y
descargar la especificación OpenAPI.

## 4. Ejemplos

### GET sin filtros (total de ventas)

```bash
curl http://127.0.0.1:8000/v1/estadisticas/ventas
```

### GET con filtros combinados

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

### Significado de cada campo de la respuesta

| Campo | Significado |
|---|---|
| `suma` | Total de `MONTO_APLICADO` de las ventas filtradas |
| `conteo` | Cantidad de ventas que coinciden con el filtro |
| `promedio` | `suma / conteo` |
| `minimo` / `maximo` | Venta más baja / más alta del subconjunto |
| `mediana` | Valor central (si el conteo es par, promedio de los 2 centrales) |
| `desviacion_estandar` | Qué tan dispersos están los montos respecto al promedio |

## 5. Errores

Todo error (filtro inválido, o filtro válido que no encuentra ninguna
venta) responde con el mismo formato JSON:

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
| **400** | Un filtro trae una clave no reconocida o un valor que no calza con el tipo esperado (ej. `canal=FAX`, `edad=abc`) | `VF` (Validación Fallida) |
| **500** | Los filtros son válidos pero no hay ninguna venta que coincida — las métricas (promedio, mediana, etc.) quedan indefinidas | `IE` (Error Interno) |

**Ejemplos que gatillan cada error:**
- `GET /v1/estadisticas/ventas?canal=FAX` → 400 (canal no es uno de los soportados).
- `POST` con `{"consulta": "NO_EXISTE", "valor": "x"}` → 400 (clave de filtro no reconocida).
- `GET /v1/estadisticas/ventas?local=999999999` → 500 (ese local no existe, no hay ventas para calcular).
