"""Configuración centralizada de logging con loguru.

Se usa `loguru` en vez de configurar `logging.handlers.RotatingFileHandler`
a mano: con una sola llamada a `logger.add(...)` ya maneja rotación,
retención y formato del archivo.

Cualquier módulo de la app registra eventos con:

    from app.logging_config import logger
    logger.info("...")

Convención de niveles (para mantener el log legible: una línea por
*operación de negocio*, no por cada paso interno):

- `debug`   : detalle técnico interno, solo va al archivo (no a consola).
- `info`    : inicio/ciclo de vida de una operación (ej. "iniciando carga...").
- `success` : una operación de negocio terminó bien (ej. carga completa, una
              consulta GET/POST resuelta). Es el nivel para "todo salió bien",
              no solo para errores.
- `warning` : algo inválido pero esperable (ej. 400 - filtro no reconocido).
- `error` / `exception` : falla interna (ej. 500), con traceback.
"""

import sys
from pathlib import Path

from loguru import logger

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Formato legible para humanos: sin milisegundos ni ruta completa del módulo.
_FORMATO_CONSOLA = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan> - <level>{message}</level>"
)
_FORMATO_ARCHIVO = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.remove()  # quita el handler default de loguru para configurar el propio
logger.add(sys.stderr, level="INFO", format=_FORMATO_CONSOLA, colorize=True)
logger.add(
    LOGS_DIR / "app.log",
    level="DEBUG",
    format=_FORMATO_ARCHIVO,
    rotation="10 MB",
    retention="10 days",
    encoding="utf-8",
    backtrace=True,
    diagnose=False,
    enqueue=True,  # escritura segura si en el futuro escriben varios procesos
)

__all__ = ["logger"]
