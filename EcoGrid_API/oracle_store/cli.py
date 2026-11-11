"""
Interfaz de línea de comandos para verificar o ejecutar la carga Oracle desde un JSON.
Uso:
    python -m oracle_store.cli --file data/raw/ree_esios_20261028_162855.json --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from oracle_store.service import DryRunReport, dry_run_file, persist_to_oracle
from oracle_store.transformers import SOURCE_OMIE, SOURCE_OPEN_METEO, SOURCE_REE


def _format_dry_run_report(report: DryRunReport, file_path: Path) -> str:
    lines = [
        f"[DRY-RUN] Archivo: {file_path}",
        f"Fuente detectada: {report.source}",
        "No se abrió conexión a Oracle.",
        "Filas a escribir/asegurar por tabla:",
        f"  - TiempoHorario: {report.tiempo_horario_rows} filas (asegurar existencia UTC)",
        f"  - {report.target_table}: {report.fact_rows} filas (MERGE idempotente)",
        f"Primera hora UTC: {report.first_utc or 'N/A'}",
        f"Última hora UTC:  {report.last_utc or 'N/A'}",
        f"Horas parciales descartadas (sin fila): {len(report.partial_hours_discarded)}",
    ]

    for item in report.partial_hours_discarded:
        lines.append(f"  - {item['fec_hora_utc']}: {item['reason']}")

    if report.partial_series_nulls:
        lines.append(
            f"Series parciales dejadas en NULL (fila conservada): {len(report.partial_series_nulls)}"
        )
        for item in report.partial_series_nulls:
            lines.append(
                f"  - {item['fec_hora_utc']} | {item['series']} ({item['points']}/12 puntos) -> {item['column']}=NULL"
            )

    lines.append(f"Avisos ({len(report.warnings)}):")
    if report.warnings:
        for warning in report.warnings:
            lines.append(f"  - {warning}")
    else:
        lines.append("  - Ninguno")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persistir o simular la carga en Oracle de un JSON de REE, OMIE u Open-Meteo."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Ruta al archivo JSON descargado.",
    )
    parser.add_argument(
        "--source",
        choices=[SOURCE_REE, SOURCE_OMIE, SOURCE_OPEN_METEO],
        default=None,
        help="Fuente opcional; por defecto se autodetecta según el contenido del JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula transformación y muestra conteos/avisos sin abrir conexión a Oracle.",
    )

    args = parser.parse_args(argv)
    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"Error: el archivo no existe: {file_path}", file=sys.stderr)
        return 1

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.dry_run:
        try:
            report = dry_run_file(file_path, source=args.source)
        except Exception as exc:
            print(f"Error en dry-run: {exc}", file=sys.stderr)
            return 1
        print(_format_dry_run_report(report, file_path))
        return 0

    result = persist_to_oracle(args.source, file_path)
    if result.executed:
        print(
            f"[OK] {result.source} -> {result.target_table}: "
            f"{result.rows_merged} filas merged, {result.tiempo_rows_ensured} horas en TiempoHorario."
        )
        return 0

    if result.skipped:
        print(f"[OMITIDO] {result.source}: {result.reason}")
        return 0

    print(f"[ERROR] {result.source}: {result.reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

