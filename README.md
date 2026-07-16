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
