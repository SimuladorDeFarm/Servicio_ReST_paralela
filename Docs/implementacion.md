# Implementación de la solución

Documento técnico: cómo está construido el servicio, módulo por módulo, y
las decisiones de diseño detrás de cada uno. Complementa a `CLAUDE.md` (el
enunciado y el plan original) explicando el **estado final implementado**.

## 1. Arquitectura general

```
1. Carga (arranque de la app, una sola vez)
   data_loader  --chunking + ProcessPoolExecutor-->  DataFrame limpio
                                                          |
                                                          v
                                                     data_store (singleton)

2. Por cada request GET/POST
   request --> schemas (valida) --> filters (aplica filtros sobre data_store)
                                          --> stats (calcula métricas)
                                               --> schemas (arma respuesta)

3. Cualquier excepción de (1) o (2)
   filters.FiltroInvalidoError / stats.SinDatosError / RequestValidationError
   / Exception  -->  errors (exception handlers globales)  --> JSON de error
```

El paralelismo "propio" que exige el ramo está en la **fase de carga**
(`data_loader`): el CSV se trocea y cada proceso worker lee, parsea y limpia
su propio rango de bytes. Los cálculos de estadísticas por request usan
pandas/numpy vectorizado (rápido, pero no paralelismo explícito — el
enunciado no lo exige ahí, y a esa escala no hace falta).

## 2. Módulos (`app/`)

### `data_loader.py` — carga paralela del CSV

- **Partición por offsets de bytes**: el archivo se divide en `n_workers ×
  chunks_per_worker` rangos `(start, end)`, ajustando cada frontera al inicio
  de la siguiente línea completa (nunca parte un registro).
- Cada rango se procesa en un `ProcessPoolExecutor` worker: abre el archivo,
  lee **solo su rango**, lo parsea con pandas y lo limpia/tipa
  (`clean_chunk`). Así el I/O y el parseo ocurren en paralelo, no solo la
  limpieza.
- `clean_chunk` es una función pura compartida por la ruta paralela y la
  secuencial (`load_csv_sequential`, usada como baseline de comparación):
  parsea fechas con formato explícito, deriva `EDAD`, normaliza `GENERO` a
  las etiquetas textuales del enunciado, tipa columnas (categorías para
  `CANAL`/`LOCAL`/`PRODUCTO`/`GENERO`, enteros/floats reducidos).
- **Formato real del CSV** (difiere de lo documentado originalmente):
  separador `;`, campos entre comillas, cabeceras con espacios
  (`MONTO APLICADO`, etc.) en vez de guion bajo. El loader normaliza esas
  cabeceras a los nombres canónicos (`MONTO_APLICADO`, etc.) usados por el
  resto de la app.
- **EDAD** se calcula como años cumplidos entre `FECHA_NACIMIENTO` y la
  `FECHA` de la venta (determinista, no depende de "hoy").
- **Rendimiento medido** contra el archivo real (634 MB, 3.242.878 filas,
  16 CPUs): secuencial ~10.4 s, paralelo ~4.0 s con 16 workers × 2
  chunks/worker (**speedup ~2.6x**). El techo lo pone la serialización
  (pickle) del DataFrame que cada worker devuelve al proceso principal —
  las columnas de texto (nombres, UUIDs) dominan esa transferencia.

### `data_store.py` — estructura en memoria (singleton)

Singleton a nivel de módulo: `set_ventas_df(df)` lo llena una sola vez (en
el `lifespan` de `main.py`); `get_ventas_df()` lo lee desde los endpoints.
Lanza `RuntimeError` si se consulta antes de cargar. Deliberadamente
desacoplado de `app.state`/FastAPI para que `filters`/`stats`/`endpoints` lo
importen sin depender de `main` (evita imports circulares).

### `schemas.py` — modelos Pydantic (request/response/Swagger)

- `TipoConsulta`: enum con las 8 claves de filtro soportadas.
- `ConsultaFiltro`: un filtro individual (`consulta` + `valor` textual).
- `EstadisticasVentasRequest`: body del POST; `consultas` es una lista que
  **por defecto es vacía** (consultas sin filtros son válidas y devuelven el
  total, según el enunciado).
- `EstadisticasVentasQueryParams`: los mismos filtros como query params
  opcionales del GET, para usar con `Depends()`.
- `EstadisticasVentasResponse` / `ErrorResponse`: forma exacta de éxito y de
  error. Todos los modelos incluyen `description` y ejemplos
  (`json_schema_extra`) para que Swagger (`/docs`) los muestre completos.

### `filters.py` — validación y aplicación de filtros

Mapeo de cada clave de filtro a la columna real del DataFrame:

| Filtro | Columna | Conversión |
|---|---|---|
| GENERO | `GENERO` | debe ser una de las 4 etiquetas válidas |
| EDAD | `EDAD` | `int(valor)` |
| CANAL | `CANAL` | debe ser uno de los 6 canales válidos |
| CODIGO_PRODUCTO | `SKU` | `int(valor)` |
| ID_PERSONA | `CODIGO_CLIENTE` | string, no vacío |
| LOCAL | `LOCAL` | `int(valor)` |
| FECHA_DESDE / FECHA_HASTA | `FECHA` | `pd.to_datetime(valor)`, límite inclusivo |

`aplicar_filtros(df, filtros)` construye una máscara booleana por cada
filtro y las combina con AND (`fillna(False)` antes de combinar, para que
los `NaN`/`NaT` de columnas nullable — ej. `EDAD` sin fecha de nacimiento
válida — no rompan el indexado booleano de pandas). Lista de filtros vacía
devuelve el DataFrame completo. Cualquier valor no convertible o fuera de
los valores permitidos lanza `FiltroInvalidoError`.

### `stats.py` — cálculo de métricas (funciones puras)

Siete funciones independientes (`conteo`, `suma`, `promedio`, `minimo`,
`maximo`, `mediana`, `desviacion_estandar`) que operan sobre una
`pd.Series` genérica — no asumen `MONTO_APLICADO` ni ninguna columna en
particular, así quedan desacopladas del schema del CSV. `calcular_estadisticas`
las combina en un dict con las claves exactas de la respuesta.

Decisiones de diseño:
- **Desviación estándar poblacional** (`ddof=0`), no muestral: es un
  resumen descriptivo del subconjunto filtrado completo, no una estimación
  inferencial sobre una muestra.
- **Conjunto vacío**: `conteo` y `suma` están definidos (dan 0), pero
  `promedio`/`minimo`/`maximo`/`mediana`/`desviacion_estandar` son
  matemáticamente indefinidos sobre 0 elementos → lanzan `SinDatosError`
  (subclase de `ValueError`), que `errors.py` traduce a 500.
- **Qué columna se mide**: siempre `MONTO_APLICADO` (el monto pagado). Los
  filtros (incluido EDAD) acotan qué filas entran al cálculo; ninguno
  cambia qué columna se agrega. Ampliar esto a "elegir la métrica" (ej.
  promedio de edad en vez de promedio de venta) requeriría un campo nuevo
  en el request — no está en el enunciado actual.

### `errors.py` — exception handlers globales

Arma el JSON de error exacto pedido (9 campos: `detail`, `instance`,
`status`, `title`, `type`, `timestamp`, `errorCode`, `errorLabel`, `method`)
sin importar en qué capa se originó la falla:

| Excepción capturada | Status | `errorCode` |
|---|---|---|
| `filters.FiltroInvalidoError` | 400 | `VF` |
| `RequestValidationError` (Pydantic/FastAPI — clave no reconocida, tipo incorrecto) | 400 | `VF` |
| `stats.SinDatosError` | 500 | `IE` |
| `Exception` (red de seguridad, cualquier falla no prevista) | 500 | `IE` |

`endpoints.py` no captura ninguna excepción: las deja propagar y estos
handlers globales las traducen en un único lugar (separación de
responsabilidades — orquestar vs. dar formato al error).

Nota sobre el `timestamp`: Python entrega precisión de microsegundos (6
dígitos); se rellena con ceros hasta 9 para calzar con el formato del
ejemplo del enunciado, sin pretender una precisión de nanosegundos real.

### `endpoints.py` — handlers GET/POST

Ambos métodos comparten la misma función interna
(`_resolver_estadisticas`): el GET normaliza sus query params al mismo
formato `ConsultaFiltro` que usa el POST (`_query_params_a_consultas`), así
la lógica de filtrado + cálculo no se duplica entre los dos métodos.

Flujo: `data_store.get_ventas_df()` → `filters.aplicar_filtros(df,
consultas)` → `stats.calcular_estadisticas(subconjunto["MONTO_APLICADO"])`
→ `EstadisticasVentasResponse`.

### `logging_config.py` — logging centralizado (loguru)

Se usa `loguru` en vez de configurar `RotatingFileHandler` a mano.
Convención de niveles (una línea por *operación de negocio*, no por cada
paso interno, para que el log quede legible):

| Nivel | Cuándo |
|---|---|
| `info` | Inicio de una operación (ej. "iniciando carga...") |
| `success` | Operación terminada bien (carga completa, consulta resuelta) |
| `warning` | 400 — filtro inválido o clave no reconocida |
| `error` / `exception` | 500 — falla interna, con traceback en el archivo |

Consola: formato colorizado, legible, sin milisegundos. Archivo
(`logs/app.log`): texto plano con módulo:función:línea, rotación (10 MB) y
retención (10 días) manejadas por la librería. `enqueue=True` para
escritura segura si en el futuro varios procesos loguean a la vez.

### `main.py` — arranque de la app

El `lifespan` de FastAPI ejecuta la carga (`data_loader.load_csv`) antes de
aceptar requests — carga desatendida, sin pasos manuales. Si falla, se
loguea con traceback y la app no llega a levantar (falla rápido y visible,
en vez de arrancar sin datos). Configurable por variables de entorno
(`VENTAS_CSV_PATH`, `VENTAS_N_WORKERS`, `VENTAS_CHUNKS_PER_WORKER`).

## 3. Supuestos y decisiones pendientes de confirmar

- **EDAD** se calcula respecto a la fecha de la venta, no a "hoy". Si la
  cátedra espera otra definición, solo cambia `data_loader._derive_edad`.
- **Desviación estándar poblacional** (`ddof=0`); si se espera muestral
  (`ddof=1`), es un cambio de una línea en `stats.desviacion_estandar`.
- **Métrica fija en `MONTO_APLICADO`**: no hay forma de pedir estadísticas
  sobre otra columna (ej. `UNIDADES` o `EDAD`) — el enunciado no da un
  mecanismo para elegirla.
- El CSV real tiene un formato distinto al documentado originalmente en el
  enunciado (separador `;`, comillas, cabeceras con espacios) — el loader ya
  lo maneja, pero vale la pena confirmarlo si llega un CSV de otra fuente.
