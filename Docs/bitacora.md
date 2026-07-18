# Bitácora de desarrollo

Registro del proceso de diseño, implementación y corrección del servicio REST
de estadísticas de ventas para Cruz Morada, en el contexto del ramo de
Computación Paralela.

---

## 1. Punto de partida

Partimos con un MVP funcional: una API en FastAPI que cargaba un CSV de
~635 MB con ventas de farmacia, lo procesaba en paralelo usando
`ProcessPoolExecutor` y exponía un endpoint (`GET` y `POST`) para consultar
estadísticas (suma, conteo, promedio, mínimo, máximo, mediana, desviación
estándar) sobre el monto de las ventas, filtrando por distintos criterios.

El código base ya resolvía el problema central — la carga paralela por
chunking de bytes y el cálculo de métricas con pandas — pero al contrastarlo
con la pauta de evaluación y los requisitos del enunciado, identificamos
varias brechas que podían costarnos puntos en la entrega.

## 2. Auditoría contra la rúbrica

Antes de tocar código, hicimos una revisión sistemática contrastando cada
módulo contra los cinco criterios de la rúbrica:

| Criterio | Peso | Estado inicial |
|---|---|---|
| Funcionalidad de endpoints | 30% | Riesgo alto |
| Formato de errores | 20% | Parcial |
| Cálculo correcto de estadísticas | 20% | Riesgo medio |
| Manejo de filtros y validaciones | 15% | Riesgo alto |
| Código limpio y documentado | 15% | Parcial |

Los hallazgos más críticos fueron:

- **Los query params del GET estaban en minúsculas** (`genero`, `canal`, etc.)
  cuando la pauta los define en mayúsculas (`GENERO`, `CANAL`). Si el
  profesor probaba con mayúsculas, Pydantic ignoraba el parámetro
  silenciosamente y la API devolvía estadísticas sin filtrar — un error
  invisible y grave.
- **FECHA_HASTA excluía casi todo el último día**: una fecha como
  `2024-05-31` se interpretaba como `2024-05-31 00:00:00`, dejando fuera
  todas las ventas del día 31 posteriores a medianoche. En el caso de mayo,
  esto eran 8.895 ventas y ~$54.8 millones de diferencia.
- **El body del POST aceptaba consultas vacías** y campos desconocidos sin
  error, cuando debería dar 400.
- **No existían pruebas unitarias** en la rama de trabajo, a pesar de ser
  un entregable obligatorio.

Documentamos todo en un archivo `pendientes.md` que usamos como checklist
durante toda la implementación.

## 3. Definición de la ruta de implementación

Con los problemas priorizados por impacto en la rúbrica, definimos 8 fases
de implementación secuenciales. La idea era atacar primero lo que más
puntos ponía en riesgo y avanzar hacia mejoras incrementales:

1. **Correcciones críticas** (filtros mayúsculas, FECHA_HASTA, consultas
   vacías, campos desconocidos)
2. **Validaciones faltantes** (UUID en ID_PERSONA, rango de fechas invertido)
3. **Formato de errores completo** (404, 405 con los 9 campos)
4. **Seguridad** (HTTPS, API Key, rate limiting, CORS, minimización de datos)
5. **Observabilidad** (middleware de logging HTTP)
6. **Documentación y Swagger**
7. **Entregables faltantes** (tests, script de descarga)
8. **Recálculo de datos de prueba** (actualizar `datos.json` con valores
   correctos)

Decidimos implementar cada fase completa antes de pasar a la siguiente, con
tests que validaran cada corrección antes de avanzar.

## 4. Decisiones técnicas y alternativas evaluadas

### 4.1 Query params en mayúsculas

Evaluamos tres alternativas:

1. **`alias="GENERO"` en cada campo**: FastAPI dejaba de aceptar el nombre
   en minúsculas. Descartado porque rompía la retrocompatibilidad sin aviso.

2. **`AliasChoices` con `validation_alias`**: Pydantic v2 soporta múltiples
   alias, pero descubrimos que `validation_alias` no funciona con
   `Depends()` para query params en FastAPI — los alias se ignoran durante
   la extracción de parámetros de la URL. Descartado tras pruebas fallidas.

3. **Renombrar los campos directamente a mayúsculas**: Rompe la convención
   Python de nombres en snake_case, pero calza exactamente con lo que pide
   la pauta y es la solución más simple y predecible. Elegimos esta opción
   porque priorizar la convención del lenguaje sobre el requisito del
   enunciado no tenía sentido en el contexto de la evaluación.

### 4.2 FECHA_HASTA — inclusión del día completo

El problema era que `pd.to_datetime("2024-05-31")` produce
`2024-05-31 00:00:00`, excluyendo casi todo el día. Evaluamos:

1. **Sumar un día y usar `<` en vez de `<=`**: Funcionalmente correcto,
   pero cambiaba la semántica del operador en un solo filtro respecto a los
   demás. Descartado por inconsistencia.

2. **Extender a fin del día (`23:59:59.999999`) cuando no tiene componente
   de hora**: Mantiene el operador `<=` consistente con los demás filtros.
   La detección es simple: si la fecha es igual a su `normalize()` (es
   decir, no tiene hora), se extiende. Si el usuario envía una fecha con
   hora explícita, se respeta tal cual. Elegimos esta opción.

### 4.3 Desviación estándar: poblacional vs. muestral

Usamos `ddof=0` (poblacional) porque las estadísticas son un resumen
descriptivo del subconjunto completo filtrado, no una estimación inferencial
sobre una muestra. Si el profesor esperara muestral (`ddof=1`), el cambio
es de una línea.

### 4.4 EDAD: cálculo respecto a la fecha de venta

La edad se calcula como años cumplidos entre `FECHA_NACIMIENTO` y la
`FECHA` de la venta, no respecto a "hoy". Esto hace que los resultados
sean deterministas y reproducibles — la misma consulta siempre da el mismo
resultado sin importar cuándo se ejecute.

### 4.5 Script de descarga del CSV

Inicialmente implementamos la descarga con `urllib.request` (sin
dependencias externas). Funcionaba para archivos públicos pequeños, pero
Google Drive requiere manejo de cookies de confirmación para archivos
grandes (~635 MB). Migramos a `gdown`, que resuelve esto automáticamente.

### 4.6 Formato de errores: handler centralizado

Evaluamos dos enfoques:

1. **Try/catch en cada endpoint**: Duplicaba lógica de formateo en cada
   handler. Descartado.

2. **Exception handlers globales en `errors.py`**: Un único punto donde
   todas las excepciones se traducen al formato de 9 campos. Los endpoints
   no capturan excepciones — las dejan propagar. Elegimos esto por
   separación de responsabilidades y porque garantiza que *todo* error
   (incluidos los que no anticipamos) salga con el formato correcto.

Extendimos el handler para cubrir `StarletteHTTPException`, lo que nos
permitió formatear 404 (ruta no encontrada) y 405 (método no permitido)
con los mismos 9 campos, sin que FastAPI devolviera su formato genérico.

## 5. Consideraciones de seguridad

Al analizar la superficie de exposición de la API, identificamos varios
vectores de riesgo que decidimos mitigar:

### 5.1 Tráfico sin cifrar (HTTPS)

La API transmite estadísticas agregadas, pero las peticiones pueden
contener parámetros que revelan patrones de consulta (qué productos, qué
locales, qué clientes se están analizando). Sin HTTPS, un atacante en la
misma red podría interceptar este tráfico.

Configuramos soporte para HTTPS a través de los flags `--ssl-keyfile` y
`--ssl-certfile` de uvicorn, con instrucciones para generar certificados
autofirmados para desarrollo. En producción se usarían certificados
firmados por una CA.

### 5.2 Autenticación (API Key)

Sin autenticación, cualquier persona que descubriera la URL podría
consultar la API sin restricción. Implementamos autenticación por API Key
(`X-API-Key` header) con las siguientes decisiones:

- **Opcional por diseño**: si la variable de entorno `API_KEY` no está
  definida, la API funciona sin autenticación. Esto facilita el desarrollo
  local sin tener que configurar credenciales en cada sesión.
- **Módulo separado (`auth.py`)**: la lógica de autenticación está
  desacoplada de los endpoints, inyectada como dependencia de FastAPI en
  el router.
- **Respuesta 401 con formato consistente**: el error de autenticación
  usa los mismos 9 campos que cualquier otro error, con `errorCode: "NA"`
  (No Autorizado).

### 5.3 Rate limiting

Un cliente malicioso o un script mal configurado podría enviar miles de
peticiones pesadas (filtros que recorren millones de filas). Integramos
`slowapi` con un límite de 60 peticiones por minuto por IP. La respuesta
429 usa el formato de 9 campos con `errorCode: "DL"` (Demasiadas
Solicitudes).

### 5.4 CORS

Configuramos `CORSMiddleware` con política restrictiva:

- Solo métodos `GET` y `POST` (los que la API soporta).
- Solo headers `Content-Type` y `X-API-Key`.
- Orígenes configurables por variable de entorno (`CORS_ORIGINS`).

Esto previene que un sitio web malicioso haga peticiones a la API desde
el navegador del usuario sin su conocimiento.

### 5.5 Minimización de datos personales

El CSV contiene columnas con datos personales sensibles: RUT del cliente,
nombres, apellidos, fecha de nacimiento y número de boleta. Aunque la API
solo devuelve estadísticas agregadas y nunca expone registros individuales,
toda esa información quedaba cargada en memoria en el DataFrame.

Decidimos eliminar estas columnas inmediatamente después de la carga y
limpieza del CSV (en `data_loader._finalize()`), antes de guardar el
DataFrame en `data_store`. Las columnas eliminadas son:
`RUN_CLIENTE`, `NOMBRES`, `APELLIDOS`, `FECHA_NACIMIENTO`, `BOLETA`.

La columna `FECHA_NACIMIENTO` ya se usó para derivar `EDAD` durante la
carga, así que no se pierde funcionalidad. Las demás no participan en
ningún filtro ni métrica. Esto reduce tanto la superficie de exposición
como el consumo de memoria.

### 5.6 Logging y trazabilidad

Implementamos un middleware HTTP que registra cada petición con:
método, ruta, query params, código de respuesta, tiempo de procesamiento
y User-Agent. Los logs se escriben en `logs/app.log` con rotación
automática (10 MB) y retención (10 días).

Esto permite auditar quién consultó qué, cuándo y desde dónde — útil
tanto para debugging como para detectar patrones de uso anómalos.

## 6. Pruebas

Creamos 44 tests organizados en 4 archivos por fase:

- **test_fase1.py** (20 tests): filtros GET en mayúsculas, FECHA_HASTA
  día completo, consultas vacías → 400, campos desconocidos → 400.
- **test_fase2.py** (11 tests): validación UUID en ID_PERSONA, rango de
  fechas invertido.
- **test_fase3.py** (6 tests): formato 404 y 405 con 9 campos.
- **test_fase4.py** (7 tests): autenticación API Key, minimización de
  datos personales.

Todos los tests corren contra una fixture en memoria (un DataFrame de
5 filas construido en `conftest.py`), sin depender del CSV real. Son
rápidos (~0.5s) y deterministas.

Para pruebas E2E contra el CSV real, mantenemos `datos.json` con casos
de prueba (request + respuesta esperada) y un script `probar_api.py` que
los ejecuta contra una instancia corriendo.

## 7. Recálculo de datos de prueba

Tras la corrección de FECHA_HASTA, los valores esperados del caso
`rango_fechas_mayo_2024` en `datos.json` quedaron desactualizados.
Creamos un script (`scripts/recalcular_datos.py`) que:

1. Carga el CSV con el mismo pipeline que la API.
2. Aplica los filtros de cada caso.
3. Recalcula las estadísticas y compara con los valores anteriores.
4. Actualiza `datos.json` automáticamente.

El recálculo confirmó el impacto de la corrección:

| Métrica | Antes | Después |
|---|---|---|
| Conteo | 282.588 | 291.483 (+8.895) |
| Suma | $1.786.662.579 | $1.841.523.386 (+$54.8M) |

Las 8.895 ventas faltantes correspondían a transacciones del 31 de mayo
realizadas después de las 00:00, que la versión anterior excluía
incorrectamente.

## 8. Resultado final

Las 8 fases de la ruta de implementación quedaron completadas. Los cinco
criterios de la rúbrica pasaron de estado "riesgo" a "OK":

| Criterio | Peso | Estado |
|---|---|---|
| Funcionalidad de endpoints | 30% | ✅ |
| Formato de errores | 20% | ✅ |
| Cálculo correcto de estadísticas | 20% | ✅ |
| Manejo de filtros y validaciones | 15% | ✅ |
| Código limpio y documentado | 15% | ✅ |

El servicio expone un endpoint con dos métodos (GET y POST), soporta 8
tipos de filtro, calcula 7 métricas estadísticas, devuelve errores en
formato consistente de 9 campos para todos los códigos HTTP (400, 401,
404, 405, 429, 500), cuenta con 44 tests automatizados, documentación
técnica y de usuario actualizadas, y medidas de seguridad que cubren
cifrado, autenticación, rate limiting, CORS y minimización de datos
personales.
