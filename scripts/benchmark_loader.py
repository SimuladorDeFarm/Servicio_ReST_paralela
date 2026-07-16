"""Mide y compara la carga secuencial vs. paralela del CSV de ventas.

Uso:
    python -m scripts.benchmark_loader data/ventas_completas.csv
    python -m scripts.benchmark_loader data/ventas_completas.csv --workers 8 --chunks-per-worker 2

Reporta tiempos, speedup, filas cargadas y uso de memoria del DataFrame, y
verifica que la carga paralela y la secuencial produzcan el mismo resultado.
"""

import argparse
import os
import time

import pandas as pd

from app import data_loader


def _cronometrar(fn, *args, **kwargs):
    inicio = time.perf_counter()
    resultado = fn(*args, **kwargs)
    return resultado, time.perf_counter() - inicio


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="ruta al CSV a cargar")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--chunks-per-worker", type=int, default=1)
    parser.add_argument(
        "--skip-sequential",
        action="store_true",
        help="omite el baseline secuencial (útil si el archivo es enorme)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="no comparar paralelo vs secuencial fila a fila",
    )
    args = parser.parse_args()

    tamano_mb = os.path.getsize(args.csv) / (1024 * 1024)
    print(f"Archivo: {args.csv}  ({tamano_mb:.1f} MB)")
    print(f"CPUs disponibles: {os.cpu_count()}  |  workers: {args.workers}  "
          f"|  chunks/worker: {args.chunks_per_worker}\n")

    df_seq = None
    t_seq = None
    if not args.skip_sequential:
        df_seq, t_seq = _cronometrar(data_loader.load_csv_sequential, args.csv)
        print(f"Secuencial : {t_seq:8.2f} s   ({len(df_seq):,} filas)")

    df_par, t_par = _cronometrar(
        data_loader.load_csv,
        args.csv,
        n_workers=args.workers,
        chunks_per_worker=args.chunks_per_worker,
    )
    print(f"Paralelo   : {t_par:8.2f} s   ({len(df_par):,} filas)")

    if t_seq is not None:
        print(f"\nSpeedup    : {t_seq / t_par:.2f}x")

    mem_mb = df_par.memory_usage(deep=True).sum() / (1024 * 1024)
    print(f"Memoria DF : {mem_mb:.1f} MB")

    if df_seq is not None and not args.no_verify:
        try:
            pd.testing.assert_frame_equal(df_seq, df_par)
            print("Verificación: OK (paralelo == secuencial)")
        except AssertionError as exc:
            print(f"Verificación: DIFIERE\n{exc}")

    print("\nTipos resultantes:")
    print(df_par.dtypes.to_string())


if __name__ == "__main__":
    main()
