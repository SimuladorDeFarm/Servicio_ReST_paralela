"""Descarga el CSV de ventas desde Google Drive.

Uso:
    python -m scripts.descargar_csv
    python -m scripts.descargar_csv --destino otra/ruta/ventas.csv
"""

import argparse
import os
import sys
import urllib.request
from pathlib import Path

DRIVE_FILE_ID = "15jLBlJ9eMQSoHsoCMnFWBGopr98FIHlK"
DESTINO_DEFAULT = "data/ventas_completas.csv"


def _url_descarga(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"


def _progreso(bloques: int, tam_bloque: int, tam_total: int) -> None:
    descargado = bloques * tam_bloque
    if tam_total > 0:
        pct = min(100, descargado * 100 // tam_total)
        mb = descargado / (1024 * 1024)
        sys.stdout.write(f"\r  {pct}% ({mb:.1f} MB)")
    else:
        mb = descargado / (1024 * 1024)
        sys.stdout.write(f"\r  {mb:.1f} MB descargados")
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", default=DESTINO_DEFAULT, help="Ruta destino del CSV")
    parser.add_argument("--file-id", default=DRIVE_FILE_ID, help="ID del archivo en Google Drive")
    args = parser.parse_args()

    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        tam_mb = destino.stat().st_size / (1024 * 1024)
        print(f"El archivo ya existe: {destino} ({tam_mb:.1f} MB)")
        print("Elimínelo manualmente si desea descargarlo de nuevo.")
        return

    url = _url_descarga(args.file_id)
    print(f"Descargando CSV desde Google Drive (ID: {args.file_id})...")
    print(f"  Destino: {destino}")

    try:
        urllib.request.urlretrieve(url, str(destino), reporthook=_progreso)
    except Exception as exc:
        print(f"\nError al descargar: {exc}")
        if destino.exists():
            destino.unlink()
        sys.exit(1)

    print()
    tam_mb = destino.stat().st_size / (1024 * 1024)
    print(f"Descarga completa: {destino} ({tam_mb:.1f} MB)")


if __name__ == "__main__":
    main()
