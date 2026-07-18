"""Verifica que el logger centralizado escriba en logs/app.log."""

from app.logging_config import LOGS_DIR, logger


def test_logs_dir_existe():
    assert LOGS_DIR.is_dir()


def test_logger_escribe_en_archivo():
    logger.info("mensaje de prueba desde test_logging_config")
    logger.complete()  # fuerza el flush antes de leer el archivo

    log_file = LOGS_DIR / "app.log"
    assert log_file.exists()
    contenido = log_file.read_text(encoding="utf-8")
    assert "mensaje de prueba desde test_logging_config" in contenido
