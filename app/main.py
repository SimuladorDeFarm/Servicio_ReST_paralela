import os
import time
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from app import data_loader, data_store
from app.logging_config import logger

CSV_PATH = os.getenv("VENTAS_CSV_PATH", "data/ventas_completas.csv")
N_WORKERS = int(os.getenv("VENTAS_N_WORKERS", os.cpu_count() or 1))
CHUNKS_PER_WORKER = int(os.getenv("VENTAS_CHUNKS_PER_WORKER", 2))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "iniciando carga de '{}' con {} workers ({} chunks/worker)...",
        CSV_PATH, N_WORKERS, CHUNKS_PER_WORKER,
    )
    inicio = time.perf_counter()
    try:
        df = data_loader.load_csv(
            CSV_PATH, n_workers=N_WORKERS, chunks_per_worker=CHUNKS_PER_WORKER
        )
    except Exception:
        logger.exception("falló la carga inicial del CSV de ventas")
        raise
    duracion = time.perf_counter() - inicio
    data_store.set_ventas_df(df)
    logger.success(
        "carga completa: {:,} filas en {:.2f} s usando {} workers ({} chunks/worker)",
        len(df), duracion, N_WORKERS, CHUNKS_PER_WORKER,
    )
    yield


app = FastAPI(title="api_paralela", lifespan=lifespan)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
