"""
Gestión de la dimensión TiempoHorario y lectura de FestivosBOE (solo lectura).
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Set
from zoneinfo import ZoneInfo

from oracle_store.connection import set_cursor_inputsizes

SELECT_TIEMPO_RANGE_SQL = """
SELECT idTiempo, fecHora
FROM TiempoHorario
WHERE fecHora BETWEEN :desde AND :hasta
"""

INSERT_TIEMPO_SQL = """
INSERT INTO TiempoHorario (
    idTiempo, fecHora, fecha, hora, diaSemana, mes, year, indFinSemana, indFestivo
) VALUES (
    :idTiempo, :fecHora, :fecha, :hora, :diaSemana, :mes, :year, :indFinSemana, :indFestivo
)
"""

SELECT_FESTIVOS_RANGE_SQL = """
SELECT DISTINCT TRUNC(fecha)
FROM FestivosBOE
WHERE UPPER(TRIM(ambito)) = 'NACIONAL'
  AND TRUNC(fecha) BETWEEN :fecha_desde AND :fecha_hasta
"""


class TiempoMap(dict):
    """Diccionario {fecHora: idTiempo} que preserva estadísticas de inserción."""

    def __init__(self, *args, inserted: int = 0, existing: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.inserted = inserted
        self.existing = existing


def normalize_utc_hour(dt: datetime) -> datetime:
    """Devuelve la hora UTC truncada como datetime naive."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0, tzinfo=None)


def compute_id_tiempo(dt_utc: datetime) -> int:
    """Calcula idTiempo YYYYMMDDHH a partir de la hora UTC."""
    normalized = normalize_utc_hour(dt_utc)
    return int(normalized.strftime("%Y%m%d%H"))


def build_tiempo_horario_row(
    dt_utc: datetime,
    calendar_tz: ZoneInfo,
    national_holidays: Set[date],
) -> Dict[str, Any]:
    """Construye una fila completa de TiempoHorario a partir de una hora UTC."""
    utc_naive = normalize_utc_hour(dt_utc)
    local_dt = utc_naive.replace(tzinfo=timezone.utc).astimezone(calendar_tz)
    local_date = local_dt.date()
    dia_semana = local_dt.isoweekday()
    ind_fin_semana = 1 if dia_semana in (6, 7) else 0
    ind_festivo = 1 if local_date in national_holidays else 0

    return {
        "idTiempo": compute_id_tiempo(utc_naive),
        "fecHora": utc_naive,
        "fecha": local_date,
        "hora": local_dt.hour,
        "diaSemana": dia_semana,
        "mes": local_dt.month,
        "year": local_dt.year,
        "indFinSemana": ind_fin_semana,
        "indFestivo": ind_festivo,
    }


def fetch_national_holidays(cursor: Any, min_date: date, max_date: date) -> Set[date]:
    """Carga festivos nacionales de FestivosBOE en una única consulta para el rango dado."""
    cursor.execute(
        SELECT_FESTIVOS_RANGE_SQL,
        {"fecha_desde": min_date, "fecha_hasta": max_date},
    )
    holidays: Set[date] = set()
    for (raw_fecha,) in cursor.fetchall():
        if isinstance(raw_fecha, datetime):
            holidays.add(raw_fecha.date())
        elif isinstance(raw_fecha, date):
            holidays.add(raw_fecha)
    return holidays


def ensure_tiempo_horario(
    cursor: Any,
    utc_hours: Iterable[datetime],
    calendar_tz: ZoneInfo,
) -> Dict[datetime, int]:
    """
    Asegura que existan filas en TiempoHorario para todas las horas UTC indicadas.
    No actualiza filas existentes y devuelve {fecHora_utc_naive: idTiempo} leído de BBDD.
    """
    unique_hours = sorted({normalize_utc_hour(h) for h in utc_hours})
    if not unique_hours:
        return {}

    desde = unique_hours[0]
    hasta = unique_hours[-1]

    cursor.execute(SELECT_TIEMPO_RANGE_SQL, {"desde": desde, "hasta": hasta})
    existing_map: Dict[datetime, int] = {
        normalize_utc_hour(fec_hora): int(id_tiempo)
        for id_tiempo, fec_hora in cursor.fetchall()
    }

    missing_hours = [hr for hr in unique_hours if hr not in existing_map]
    if missing_hours:
        local_dates = [
            hr.replace(tzinfo=timezone.utc).astimezone(calendar_tz).date()
            for hr in missing_hours
        ]
        holidays = fetch_national_holidays(cursor, min(local_dates), max(local_dates))
        rows_to_insert = [
            build_tiempo_horario_row(hr, calendar_tz, holidays)
            for hr in missing_hours
        ]
        set_cursor_inputsizes(
            cursor,
            idTiempo="NUMBER",
            fecHora="TIMESTAMP",
            fecha="DATE",
            hora="NUMBER",
            diaSemana="NUMBER",
            mes="NUMBER",
            year="NUMBER",
            indFinSemana="NUMBER",
            indFestivo="NUMBER",
        )
        cursor.executemany(INSERT_TIEMPO_SQL, rows_to_insert)

    cursor.execute(SELECT_TIEMPO_RANGE_SQL, {"desde": desde, "hasta": hasta})
    db_map: Dict[datetime, int] = {
        normalize_utc_hour(fec_hora): int(id_tiempo)
        for id_tiempo, fec_hora in cursor.fetchall()
    }

    missing_after = [hr for hr in unique_hours if hr not in db_map]
    if missing_after:
        raise RuntimeError(
            f"Faltan {len(missing_after)} horas en TiempoHorario tras la inserción."
        )

    inserted_count = len(missing_hours)
    existing_count = len(unique_hours) - inserted_count

    return TiempoMap(
        {hr: db_map[hr] for hr in unique_hours},
        inserted=inserted_count,
        existing=existing_count,
    )

