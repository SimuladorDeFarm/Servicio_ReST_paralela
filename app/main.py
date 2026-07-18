import os
import time
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import data_loader, data_store, endpoints, errors
from app.logging_config import logger

CSV_PATH = os.getenv("VENTAS_CSV_PATH", "data/ventas_completas.csv")
N_WORKERS = int(os.getenv("VENTAS_N_WORKERS", os.cpu_count() or 1))
CHUNKS_PER_WORKER = int(os.getenv("VENTAS_CHUNKS_PER_WORKER", 2))


# Carga desatendida del CSV al arrancar la app (antes de aceptar requests); deja el
# resultado en data_store para que los endpoints lo lean.
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


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(title="api_paralela", lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    logger.info(
        "{} {} {} | {} | {:.1f}ms | {}",
        request.method,
        request.url.path,
        f"?{request.url.query}" if request.url.query else "",
        response.status_code,
        duracion_ms,
        request.headers.get("user-agent", "-"),
    )
    return response


app.include_router(endpoints.router)
errors.register_exception_handlers(app)


@app.exception_handler(RateLimitExceeded)
async def _handle_rate_limit(request: Request, exc: RateLimitExceeded):
    from app.errors import _cuerpo_error, _timestamp
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Demasiadas solicitudes. Límite: {exc.detail}",
            "instance": request.url.path,
            "status": 429,
            "title": "Too Many Requests",
            "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/429",
            "timestamp": _timestamp(),
            "errorCode": "DL",
            "errorLabel": "Demasiadas Solicitudes",
            "method": request.method,
        },
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
