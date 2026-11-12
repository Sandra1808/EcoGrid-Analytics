"""
Script y módulo de backfill histórico para REE (Red Eléctrica de España).
Descarga día a día los datos de demanda peninsular desde 2026-10-29 hasta la fecha actual,
guarda los JSON brutos en data/raw/ y persiste en Oracle de forma idempotente con reporte explícito.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse
import json
import logging
import sys

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store.config import OracleConfig
from oracle_store.connection import connect_oracle, verify_schema
from oracle_store.service import PersistResult, persist_to_oracle
from src.config.settings import DATA_RAW_DIR
from src.connectors.ree_client import REEClient

logger = logging.getLogger("EcoGrid.Backfill")


def run_ree_backfill(
    start_date: date,
    end_date: date,
    raw_dir: Path = DATA_RAW_DIR,
    force_download: bool = False,
    raise_on_error: bool = True,
    config: Optional[OracleConfig] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el backfill histórico de REE día a día entre start_date y end_date (inclusives).
    Retorna un diccionario detallado con las estadísticas acumuladas.
    """
    cfg = config or OracleConfig.from_env()
    issue = cfg.readiness_issue()
    if issue is not None:
        raise RuntimeError(f"Configuración Oracle no lista para backfill: {issue}")

    # Verificar conexión previa y esquema antes de iniciar el ciclo de descargas
    logger.info("Comprobando conexión y esquema Oracle antes de iniciar backfill...")
    test_conn = connect_oracle(cfg)
    try:
        verify_schema(test_conn, cfg)
        conn_info = f"usuario={cfg.user}, dsn={cfg.dsn}"
    finally:
        test_conn.close()

    raw_dir.mkdir(parents=True, exist_ok=True)
    ree_client = REEClient()

    curr_date = start_date
    days_processed = 0
    files_downloaded = 0
    files_reused = 0

    total_merged = 0
    total_inserted = 0
    total_updated = 0
    total_tiempo_inserted = 0
    total_tiempo_existing = 0

    daily_reports: List[Dict[str, Any]] = []

    print(f"\n============================================================")
    print(f" INICIO DE BACKFILL HISTÓRICO REE: {start_date} -> {end_date}")
    print(f" Conexión Oracle verificada: {conn_info}")
    print(f" Directorio destino JSON: {raw_dir}")
    print(f"============================================================\n")

    while curr_date <= end_date:
        day_str = curr_date.strftime("%Y%m%d")
        day_iso = curr_date.strftime("%Y-%m-%d")
        json_filename = f"ree_esios_backfill_{day_str}.json"
        json_path = raw_dir / json_filename

        # 1. Obtener JSON (desde disco o descargándolo de apidatos.ree.es)
        if json_path.is_file() and not force_download:
            files_reused += 1
            source_desc = f"reutilizado de disco ({json_filename})"
        else:
            day_dt = datetime.combine(curr_date, datetime.min.time())
            fetch_res = ree_client.fetch_demand(start_date=day_dt, end_date=day_dt)
            if not fetch_res.get("success") or not fetch_res.get("data"):
                err_msg = fetch_res.get("error") or "Fallo en descarga REE"
                if raise_on_error:
                    raise RuntimeError(f"Fallo al descargar {day_iso} de REE: {err_msg}")
                logger.error("Error al descargar %s: %s", day_iso, err_msg)
                curr_date += timedelta(days=1)
                continue

            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(fetch_res["data"], fh, indent=2, ensure_ascii=False)
            files_downloaded += 1
            source_desc = f"descargado con éxito ({json_filename})"

        # 2. Persistir en Oracle con modo explícito de visibilidad de errores
        res: PersistResult = persist_to_oracle(
            source="ree_esios",
            json_path=json_path,
            config=cfg,
            raise_on_error=raise_on_error,
        )

        days_processed += 1
        total_merged += res.rows_merged
        total_inserted += res.rows_inserted
        total_updated += res.rows_updated
        total_tiempo_inserted += res.tiempo_rows_inserted
        total_tiempo_existing += res.tiempo_rows_existing

        daily_info = {
            "fecha": day_iso,
            "archivo": json_filename,
            "fuente_json": source_desc,
            "filas_merged": res.rows_merged,
            "filas_insertadas": res.rows_inserted,
            "filas_actualizadas": res.rows_updated,
            "tiempo_insertadas": res.tiempo_rows_inserted,
            "tiempo_existentes": res.tiempo_rows_existing,
        }
        daily_reports.append(daily_info)

        print(
            f"[{day_iso}] {source_desc} -> DemandaGeneracionREE: "
            f"{res.rows_merged} filas ({res.rows_inserted} ins, {res.rows_updated} upd) | "
            f"TiempoHorario: ({res.tiempo_rows_inserted} ins, {res.tiempo_rows_existing} prev)"
        )

        curr_date += timedelta(days=1)

    summary = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "connection_info": conn_info,
        "days_processed": days_processed,
        "files_downloaded": files_downloaded,
        "files_reused": files_reused,
        "demanda_total_merged": total_merged,
        "demanda_total_inserted": total_inserted,
        "demanda_total_updated": total_updated,
        "tiempo_total_inserted": total_tiempo_inserted,
        "tiempo_total_existing": total_tiempo_existing,
        "daily_reports": daily_reports,
    }

    print(f"\n============================================================")
    print(f" RESUMEN FINAL DEL BACKFILL REE")
    print(f"============================================================")
    print(f"Días procesados:            {days_processed}")
    print(f"Archivos descargados a disco: {files_downloaded}")
    print(f"Archivos reutilizados:      {files_reused}")
    print(f"Filas en DemandaGeneracionREE: {total_merged}")
    print(f"  - Nuevas insertadas:      {total_inserted}")
    print(f"  - Actualizadas (MERGE):   {total_updated}")
    print(f"Horas en TiempoHorario aseguradas:")
    print(f"  - Nuevas horas insertadas: {total_tiempo_inserted}")
    print(f"  - Horas ya existentes:     {total_tiempo_existing}")
    print(f"============================================================\n")

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ejecutar backfill histórico de REE en Oracle.")
    parser.add_argument(
        "--start-date",
        default="2026-10-29",
        help="Fecha inicial en formato YYYY-MM-DD (por defecto: 2026-10-29).",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Fecha final en formato YYYY-MM-DD (por defecto: fecha actual).",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DATA_RAW_DIR),
        help=f"Directorio donde guardar los JSON brutos (por defecto: {DATA_RAW_DIR}).",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Fuerza la descarga aunque el archivo JSON ya exista en disco.",
    )
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Continúa el backfill ante errores en lugar de abortar inmediatamente.",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        s_date = datetime.strptime(args.start_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: formato inválido para --start-date: {args.start_date}", file=sys.stderr)
        return 1

    if args.end_date:
        try:
            e_date = datetime.strptime(args.end_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: formato inválido para --end-date: {args.end_date}", file=sys.stderr)
            return 1
    else:
        e_date = date.today()

    if s_date > e_date:
        print(f"Error: la fecha inicial ({s_date}) no puede ser posterior a la fecha final ({e_date})", file=sys.stderr)
        return 1

    try:
        run_ree_backfill(
            start_date=s_date,
            end_date=e_date,
            raw_dir=Path(args.raw_dir),
            force_download=args.force_download,
            raise_on_error=not args.ignore_errors,
        )
        return 0
    except Exception as exc:
        print(f"\n[ERROR CRÍTICO] El backfill falló: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

