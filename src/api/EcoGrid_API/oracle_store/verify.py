"""
Script y módulo de verificación de continuidad y completitud para REE en Oracle.
Comprueba que no existan horas faltantes (gaps) en DemandaGeneracionREE desde 2026-10-29
hasta la última fecha registrada, y reporta estadísticas de demanda real y previsiones.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import argparse
import sys

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store.config import OracleConfig
from oracle_store.connection import connect_oracle, verify_schema


def verify_ree_continuity(
    since_utc: Optional[datetime] = None,
    config: Optional[OracleConfig] = None,
) -> Dict[str, Any]:
    """
    Verifica la continuidad horaria de DemandaGeneracionREE para idCCAA=1 (Nacional '00').
    Si since_utc es None, evalúa desde 2026-10-28 23:00:00 UTC (inicio del 2026-10-29 CET).
    """
    cfg = config or OracleConfig.from_env()
    issue = cfg.readiness_issue()
    if issue is not None:
        raise RuntimeError(f"Configuración Oracle no lista: {issue}")

    start_utc = since_utc or datetime(2026, 10, 28, 23, 0, 0)

    conn = connect_oracle(cfg)
    try:
        verify_schema(conn, cfg)
        cursor = conn.cursor()

        # Obtener idCCAA nacional
        cursor.execute("SELECT idCCAA FROM ComunidadAutonoma WHERE codIne = :cod", {"cod": cfg.nacional_ccaa_codine})
        row_ccaa = cursor.fetchone()
        if not row_ccaa:
            raise RuntimeError(f"No existe ComunidadAutonoma con codIne='{cfg.nacional_ccaa_codine}'")
        id_ccaa_nacional = int(row_ccaa[0])

        # Consultar todas las filas de REE desde start_utc ordenadas cronológicamente
        query = """
        SELECT
            t.fecHora,
            d.idTiempo,
            d.demandaRealMW,
            d.demandaPrevistaREEMW,
            d.demandaProgramadaMW,
            d.demandaProgramadaTotalMW
        FROM DemandaGeneracionREE d
        JOIN TiempoHorario t ON t.idTiempo = d.idTiempo
        WHERE d.idCCAA = :id_ccaa
          AND t.fecHora >= :start_utc
        ORDER BY t.fecHora ASC
        """
        cursor.execute(query, {"id_ccaa": id_ccaa_nacional, "start_utc": start_utc})
        records = cursor.fetchall()
    finally:
        conn.close()

    if not records:
        return {
            "success": False,
            "total_records": 0,
            "message": f"No se encontraron registros en DemandaGeneracionREE a partir de {start_utc.isoformat()}Z",
            "missing_hours": [],
        }

    first_dt: datetime = records[0][0]
    last_dt: datetime = records[-1][0]

    hours_found: Set[datetime] = set()
    real_values: List[float] = []
    null_real_hours: List[datetime] = []
    prevista_count = 0
    programada_count = 0

    for fec_hora, id_tiempo, real, prev, prog, prog_tot in records:
        hours_found.add(fec_hora)
        if real is not None:
            real_values.append(float(real))
        else:
            null_real_hours.append(fec_hora)
        if prev is not None:
            prevista_count += 1
        if prog is not None:
            programada_count += 1

    # Comprobación estricta de huecos hora a hora entre first_dt y last_dt
    expected_hours: List[datetime] = []
    curr = first_dt
    while curr <= last_dt:
        expected_hours.append(curr)
        curr += timedelta(hours=1)

    missing_hours = [h for h in expected_hours if h not in hours_found]

    min_val = min(real_values) if real_values else None
    max_val = max(real_values) if real_values else None
    avg_val = round(sum(real_values) / len(real_values), 2) if real_values else None

    is_continuous = len(missing_hours) == 0

    result = {
        "success": is_continuous,
        "first_utc": first_dt.isoformat() + "Z",
        "last_utc": last_dt.isoformat() + "Z",
        "expected_hours_count": len(expected_hours),
        "actual_hours_count": len(hours_found),
        "missing_hours_count": len(missing_hours),
        "missing_hours": [h.isoformat() + "Z" for h in missing_hours],
        "hours_with_real_demand": len(real_values),
        "hours_with_null_real_demand": len(null_real_hours),
        "null_real_hours": [h.isoformat() + "Z" for h in null_real_hours],
        "hours_with_prevista": prevista_count,
        "hours_with_programada": programada_count,
        "demanda_real_min_mw": min_val,
        "demanda_real_max_mw": max_val,
        "demanda_real_avg_mw": avg_val,
    }

    print("\n============================================================")
    print(" VERIFICACIÓN DE CONTINUIDAD HISTÓRICA REE EN ORACLE")
    print("============================================================")
    print(f"Rango evaluado (UTC):       {result['first_utc']} -> {result['last_utc']}")
    print(f"Horas esperadas en rango:   {result['expected_hours_count']}")
    print(f"Horas registradas en BBDD:  {result['actual_hours_count']}")
    print(f"Horas faltantes (gaps):     {result['missing_hours_count']}")

    if is_continuous:
        print("ESTADO: CONTINUIDAD 100% GARANTIZADA - SIN HORAS FALTANTES.")
    else:
        print("ALERTA: SE DETECTARON HUECOS EN EL HISTÓRICO:")
        for h in result["missing_hours"][:10]:
            print(f"  - Faltante: {h}")
        if len(result["missing_hours"]) > 10:
            print(f"  ... y {len(result['missing_hours']) - 10} más.")

    print("------------------------------------------------------------")
    print(f"Horas con demanda real (MW):   {result['hours_with_real_demand']}")
    print(f"Horas con demanda prevista:    {result['hours_with_prevista']}")
    print(f"Horas con demanda programada:  {result['hours_with_programada']}")
    if result['hours_with_null_real_demand'] > 0:
        print(f"Horas parciales (Real=NULL):   {result['hours_with_null_real_demand']} (ej. hora en curso)")
        for h in result['null_real_hours']:
            print(f"  - {h} (en curso o incompleta)")
    if real_values:
        print(f"Estadísticas Demanda Real:     Min={min_val} MW | Avg={avg_val} MW | Max={max_val} MW")
    print("============================================================\n")

    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verificar continuidad y huecos en REE Oracle.")
    parser.add_argument(
        "--since",
        default="2026-10-28T23:00:00",
        help="Fecha inicial UTC en formato YYYY-MM-DDTHH:MM:SS (por defecto: 2026-10-28T23:00:00).",
    )
    args = parser.parse_args(argv)

    try:
        since_dt = datetime.fromisoformat(args.since.strip())
    except ValueError:
        print(f"Error: formato inválido para --since: {args.since}", file=sys.stderr)
        return 1

    res = verify_ree_continuity(since_utc=since_dt)
    return 0 if res["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

