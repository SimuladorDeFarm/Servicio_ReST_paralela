import os
import time
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from app import data_loader

CSV_PATH = os.getenv("VENTAS_CSV_PATH", "data/ventas_completas.csv")
N_WORKERS = int(os.getenv("VENTAS_N_WORKERS", os.cpu_count() or 1))
CHUNKS_PER_WORKER = int(os.getenv("VENTAS_CHUNKS_PER_WORKER", 2))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[carga] iniciando carga de '{CSV_PATH}' con {N_WORKERS} workers "
          f"({CHUNKS_PER_WORKER} chunks/worker)...")
    inicio = time.perf_counter()
    df = data_loader.load_csv(
        CSV_PATH, n_workers=N_WORKERS, chunks_per_worker=CHUNKS_PER_WORKER
    )
    duracion = time.perf_counter() - inicio
    app.state.ventas_df = df
    print(f"[carga] completa: {len(df):,} filas en {duracion:.2f} s "
          f"usando {N_WORKERS} workers ({CHUNKS_PER_WORKER} chunks/worker)")
    yield


app = FastAPI(title="api_paralela", lifespan=lifespan)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
