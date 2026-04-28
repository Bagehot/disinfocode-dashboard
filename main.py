"""
Punto de entrada principal.

Uso:
    python main.py                  # descarga todo + parsea + exporta
    python main.py --wave 8         # solo una ola
    python main.py --no-fetch       # usa caché, solo parsea y exporta
    python main.py --no-fetch --wave 8
"""

import argparse
from scraper.fetcher import fetch_all, load_cached
from scraper.parser import parse_all
from analysis.compare import build_excel, save_csv


def main():
    parser = argparse.ArgumentParser(description="Extractor de informes DisinfoCode")
    parser.add_argument("--wave", type=int, choices=[5, 6, 8], help="Procesar solo una ola")
    parser.add_argument("--no-fetch", action="store_true", help="Usar datos en caché")
    args = parser.parse_args()

    waves = [args.wave] if args.wave else None

    if args.no_fetch:
        print("Cargando datos desde caché...")
        reports = load_cached(waves)
    else:
        print("Descargando informes de disinfocode.eu...")
        reports = fetch_all(waves)

    print(f"\nInformes cargados: {len(reports)}")
    if not reports:
        print("ERROR: No se encontraron informes.")
        return

    print("\nExtrayendo métricas SLI...")
    metrics = parse_all(reports)

    table_rows = [r for r in metrics if r["value"] is not None]
    print(f"\nTotal filas con tabla: {len(table_rows)} / {len(metrics)} totales")

    if not table_rows:
        print("AVISO: No se encontraron tablas SLI con datos numéricos.")
        print("       Revisa data/raw/ para confirmar que los JSONs se descargaron.")
        return

    save_csv(metrics)
    build_excel(metrics)
    print("\nListo. Archivos en output/")


if __name__ == "__main__":
    main()
