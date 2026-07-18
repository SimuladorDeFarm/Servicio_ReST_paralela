# Logging centralizado con loguru (maneja rotación/retención sin RotatingFileHandler propio).
# Uso: from app.logging_config import logger
# Niveles: info=inicio de operación, success=operación resuelta bien, warning=400, error=500.

import sys
from pathlib import Path

from loguru import logger

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Formato legible para humanos: sin milisegundos ni ruta completa del módulo.
# Timestamps en ISO 8601 (YYYY-MM-DDTHH:mm:ss.SSSSSSZ) para trazabilidad estandarizada.
_FORMATO_CONSOLA = (
    "<green>{time:YYYY-MM-DDTHH:mm:ss.SSSSSSZ}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan> - <level>{message}</level>"
)
_FORMATO_ARCHIVO = (
    "{time:YYYY-MM-DDTHH:mm:ss.SSSSSSZ} | {level: <8} | {name}:{function}:{line} - {message}"
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
