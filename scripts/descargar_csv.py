"""Descarga el CSV de ventas desde Google Drive.

Uso:
    python -m scripts.descargar_csv
    python -m scripts.descargar_csv --destino otra/ruta/ventas.csv
"""

import argparse
import sys
from pathlib import Path

DRIVE_FILE_ID = "15jLBlJ9eMQSoHsoCMnFWBGopr98FIHlK"
DESTINO_DEFAULT = "data/ventas_completas.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", default=DESTINO_DEFAULT, help="Ruta destino del CSV")
    parser.add_argument("--file-id", default=DRIVE_FILE_ID, help="ID del archivo en Google Drive")
    args = parser.parse_args()

    try:
        import gdown
    except ImportError:
        print("Falta la librería gdown. Instálala con: pip install gdown")
        sys.exit(1)

    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        tam_mb = destino.stat().st_size / (1024 * 1024)
        print(f"El archivo ya existe: {destino} ({tam_mb:.1f} MB)")
        print("Elimínelo manualmente si desea descargarlo de nuevo.")
        return

    url = f"https://drive.google.com/uc?id={args.file_id}"
    print(f"Descargando CSV desde Google Drive (ID: {args.file_id})...")
    print(f"  Destino: {destino}")

    output = gdown.download(url, str(destino), quiet=False)

    if output is None or not destino.exists():
        print("\nError: la descarga falló. Verifica que el archivo sea público en Drive.")
        sys.exit(1)

    tam_mb = destino.stat().st_size / (1024 * 1024)
    print(f"\nDescarga completa: {destino} ({tam_mb:.1f} MB)")


if __name__ == "__main__":
    main()
