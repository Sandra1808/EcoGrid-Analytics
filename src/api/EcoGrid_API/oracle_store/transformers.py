"""
Transformadores puros (sin acceso a BBDD) para los JSON de REE, OMIE y Open-Meteo.
Convierte todas las series a granularidad horaria UTC, valida rangos y detecta
horas parciales o inválidas siguiendo estrictamente la especificación.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math

from oracle_store.config import OracleConfig

SOURCE_REE = "ree_esios"
SOURCE_OMIE = "omie"
SOURCE_OPEN_METEO = "open_meteo"

REE_SERIES_COLUMN_MAP: Dict[str, str] = {
    "real": "demandaRealMW",
    "prevista": "demandaPrevistaREEMW",
    "programada": "demandaProgramadaMW",
    "programada total": "demandaProgramadaTotalMW",
}

REE_TARGET_COLUMNS: Tuple[str, ...] = (
    "demandaRealMW",
    "demandaPrevistaREEMW",
    "demandaProgramadaMW",
    "demandaProgramadaTotalMW",
)

OPEN_METEO_FLOAT_5_2_MAP: Dict[str, str] = {
    "temperature_2m": "temperatura_2m",
    "wind_speed_10m": "viento_10m",
    "wind_speed_80m": "viento_80m",
    "wind_speed_120m": "viento_120m",
    "wind_speed_180m": "viento_180m",
}

OPEN_METEO_DIR_5_2_MAP: Dict[str, str] = {
    "wind_direction_10m": "viento_dir_10m",
    "wind_direction_80m": "viento_dir_80m",
    "wind_direction_120m": "viento_dir_120m",
    "wind_direction_180m": "viento_dir_180m",
}

OPEN_METEO_FLOAT_8_2_MAP: Dict[str, str] = {
    "direct_normal_irradiance": "radiacion_directa",
    "shortwave_radiation": "shortwave_radiation",
    "global_tilted_irradiance": "global_tilted_irradiance",
}

OPEN_METEO_PCT_INT_MAP: Dict[str, str] = {
    "cloud_cover": "cobertura_nubes",
    "relative_humidity_2m": "humedad_relativa",
}


@dataclass
class TransformResult:
    """Resultado de transformar un JSON en filas listas para persistir."""

    source: str
    target_table: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    utc_hours: List[datetime] = field(default_factory=list)
    discarded_hours: List[Dict[str, Any]] = field(default_factory=list)
    partial_series: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def first_utc(self) -> Optional[datetime]:
        return self.utc_hours[0] if self.utc_hours else None

    @property
    def last_utc(self) -> Optional[datetime]:
        return self.utc_hours[-1] if self.utc_hours else None


def _parse_finite_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def _parse_bounded_float(
    value: Any,
    min_val: float,
    max_val: float,
    decimals: int,
) -> Tuple[Optional[float], Optional[str]]:
    if value is None:
        return None, None
    num = _parse_finite_float(value)
    if num is None:
        return None, "valor no numérico"
    if not (min_val <= num <= max_val):
        return None, f"valor {num} fuera de rango [{min_val}, {max_val}]"
    return round(num, decimals), None


def _parse_bounded_int(
    value: Any,
    min_val: int,
    max_val: int,
) -> Tuple[Optional[int], Optional[str]]:
    if value is None:
        return None, None
    num = _parse_finite_float(value)
    if num is None:
        return None, "valor no numérico"
    rounded = int(round(num))
    if not (min_val <= rounded <= max_val):
        return None, f"valor {num} fuera de rango [{min_val}, {max_val}]"
    return rounded, None


def _parse_iso_aware_to_utc(dt_raw: Any) -> Optional[datetime]:
    if not isinstance(dt_raw, str) or not dt_raw.strip():
        return None
    text = dt_raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _truncate_utc_hour(dt_utc: datetime) -> datetime:
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc)
    return dt_utc.replace(minute=0, second=0, microsecond=0, tzinfo=None)


def detect_source(data: Any) -> str:
    """Autodetecta la fuente ('ree_esios', 'omie', 'open_meteo') a partir del JSON."""
    if not isinstance(data, dict):
        raise ValueError("El JSON raíz debe ser un objeto.")

    if isinstance(data.get("hourly"), dict) and "latitude" in data and "longitude" in data:
        return SOURCE_OPEN_METEO

    if data.get("market") == "OMIE" or (
        isinstance(data.get("records"), list) and "filename_original" in data
    ):
        return SOURCE_OMIE

    payload = data.get("payload")
    if isinstance(payload, dict) and (
        "included" in payload
        or "indicator" in payload
        or "ree" in str(data.get("api_origin", "")).lower()
    ):
        return SOURCE_REE

    raise ValueError(
        "No se pudo detectar la fuente del JSON (esperado REE, OMIE u Open-Meteo)."
    )


def transform_ree(
    data: Dict[str, Any],
    min_mw: float = 15000.0,
    max_mw: float = 45000.0,
) -> TransformResult:
    """
    Transforma el JSON de REE (5 min) a filas horarias UTC para DemandaGeneracionREE.
    Deduplica datetimes por serie, valida rango por punto y exige 12 puntos por hora.
    """
    result = TransformResult(source=SOURCE_REE, target_table="DemandaGeneracionREE")

    payload = data.get("payload") if isinstance(data, dict) else None
    included = payload.get("included") if isinstance(payload, dict) else None
    if not isinstance(included, list):
        result.warnings.append(
            "Formato REE sin payload.included[*] (por ejemplo ESIOS V2); no se escriben filas."
        )
        return result

    series_hourly: Dict[str, Dict[datetime, List[float]]] = {
        col: defaultdict(list) for col in REE_TARGET_COLUMNS
    }
    all_hours: set[datetime] = set()
    seen_series_cols: Dict[str, str] = {}

    for item in included:
        if not isinstance(item, dict):
            continue
        raw_type = str(item.get("type") or "").strip()
        col_name = REE_SERIES_COLUMN_MAP.get(raw_type.lower())
        if col_name is None:
            result.warnings.append(f"Serie REE desconocida ignorada: '{raw_type}'")
            continue

        seen_series_cols[col_name] = raw_type
        values = item.get("attributes", {}).get("values", [])
        if not isinstance(values, list):
            result.warnings.append(f"Serie REE '{raw_type}' sin lista attributes.values.")
            continue

        seen_instants: set[datetime] = set()
        duplicate_count = 0
        invalid_points = 0

        for point in values:
            if not isinstance(point, dict):
                invalid_points += 1
                continue
            dt_utc = _parse_iso_aware_to_utc(point.get("datetime"))
            if dt_utc is None:
                invalid_points += 1
                continue

            if dt_utc in seen_instants:
                duplicate_count += 1
                continue
            seen_instants.add(dt_utc)

            hour_utc = _truncate_utc_hour(dt_utc)
            all_hours.add(hour_utc)

            val, err = _parse_bounded_float(point.get("value"), min_mw, max_mw, 4)
            if err is not None or val is None:
                invalid_points += 1
                continue

            series_hourly[col_name][hour_utc].append(val)

        if duplicate_count:
            result.warnings.append(
                f"REE serie '{raw_type}': {duplicate_count} puntos con datetime duplicado omitidos."
            )
        if invalid_points:
            result.warnings.append(
                f"REE serie '{raw_type}': {invalid_points} puntos descartados (no numéricos o fuera de [{min_mw}, {max_mw}] MW)."
            )

    sorted_hours = sorted(all_hours)
    valid_hours: List[datetime] = []

    for hour_utc in sorted_hours:
        row: Dict[str, Any] = {"fecHora": hour_utc}
        has_valid_value = False
        hour_partials: List[Dict[str, Any]] = []

        for col_name in REE_TARGET_COLUMNS:
            pts = series_hourly[col_name].get(hour_utc, [])
            if len(pts) == 12:
                row[col_name] = round(sum(pts) / 12.0, 4)
                has_valid_value = True
            else:
                row[col_name] = None
                if col_name in seen_series_cols and len(pts) > 0:
                    hour_partials.append(
                        {
                            "fec_hora_utc": hour_utc.isoformat() + "Z",
                            "series": seen_series_cols[col_name],
                            "column": col_name,
                            "points": len(pts),
                        }
                    )

        if has_valid_value:
            result.rows.append(row)
            valid_hours.append(hour_utc)
            for p in hour_partials:
                result.partial_series.append(p)
                result.warnings.append(
                    f"Hora parcial REE {p['fec_hora_utc']} ({p['series']}: {p['points']}/12 puntos) -> {p['column']}=NULL."
                )
        else:
            result.discarded_hours.append(
                {
                    "fec_hora_utc": hour_utc.isoformat() + "Z",
                    "reason": "Ninguna serie alcanzó 12/12 puntos válidos",
                }
            )
            result.warnings.append(
                f"Hora REE descartada {hour_utc.isoformat()}Z: ninguna serie alcanzó 12/12 puntos válidos."
            )

    result.utc_hours = valid_hours
    return result


def transform_omie(
    data: Dict[str, Any],
    min_price: float = -500.0,
    max_price: float = 4000.0,
    market_tz_name: str = "Europe/Madrid",
) -> TransformResult:
    """
    Transforma el JSON de OMIE (periodos de 15 min) a filas horarias UTC para PreciosMercadoOmie.
    """
    result = TransformResult(source=SOURCE_OMIE, target_table="PreciosMercadoOmie")
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        result.warnings.append("JSON OMIE sin lista 'records'.")
        return result

    market_tz = ZoneInfo(market_tz_name)
    seen_periods: set[datetime] = set()
    hourly_es: Dict[datetime, List[float]] = defaultdict(list)
    hourly_pt: Dict[datetime, List[float]] = defaultdict(list)
    all_hours: set[datetime] = set()
    duplicate_periods = 0
    out_of_range_points = 0
    invalid_records = 0

    for rec in records:
        if not isinstance(rec, dict):
            invalid_records += 1
            continue
        try:
            year = int(rec["year"])
            month = int(rec["month"])
            day = int(rec["day"])
            period = int(rec["hour"])
            if not (1 <= period <= 100):
                raise ValueError("Periodo fuera de rango 1..100")
            midnight_utc = datetime(year, month, day, 0, 0, 0, tzinfo=market_tz).astimezone(
                timezone.utc
            )
        except (KeyError, TypeError, ValueError):
            invalid_records += 1
            continue

        period_utc = midnight_utc + timedelta(minutes=(period - 1) * 15)
        if period_utc in seen_periods:
            duplicate_periods += 1
            continue
        seen_periods.add(period_utc)

        hour_utc = _truncate_utc_hour(period_utc)
        all_hours.add(hour_utc)

        es_val, es_err = _parse_bounded_float(rec.get("price_spain"), min_price, max_price, 4)
        if es_err is not None:
            out_of_range_points += 1
        elif es_val is not None:
            hourly_es[hour_utc].append(es_val)

        pt_val, pt_err = _parse_bounded_float(rec.get("price_portugal"), min_price, max_price, 4)
        if pt_err is not None:
            out_of_range_points += 1
        elif pt_val is not None:
            hourly_pt[hour_utc].append(pt_val)

    if invalid_records:
        result.warnings.append(f"OMIE: {invalid_records} registros con fecha/periodo inválido omitidos.")
    if duplicate_periods:
        result.warnings.append(f"OMIE: {duplicate_periods} periodos duplicados omitidos.")
    if out_of_range_points:
        result.warnings.append(
            f"OMIE: {out_of_range_points} precios descartados por no numéricos o fuera de [{min_price}, {max_price}] €/MWh."
        )

    valid_hours: List[datetime] = []
    for hour_utc in sorted(all_hours):
        es_pts = hourly_es[hour_utc]
        pt_pts = hourly_pt[hour_utc]
        es_mean = round(sum(es_pts) / 4.0, 4) if len(es_pts) == 4 else None
        pt_mean = round(sum(pt_pts) / 4.0, 4) if len(pt_pts) == 4 else None

        if es_mean is None and pt_mean is None:
            result.discarded_hours.append(
                {
                    "fec_hora_utc": hour_utc.isoformat() + "Z",
                    "reason": f"Periodos válidos insuficientes (ES={len(es_pts)}/4, PT={len(pt_pts)}/4)",
                }
            )
            result.warnings.append(
                f"Hora OMIE descartada {hour_utc.isoformat()}Z: ES={len(es_pts)}/4, PT={len(pt_pts)}/4 periodos válidos."
            )
            continue

        if es_mean is None or pt_mean is None:
            result.warnings.append(
                f"Hora OMIE {hour_utc.isoformat()}Z con precio faltante (ES={'OK' if es_mean is not None else 'NULL'}, PT={'OK' if pt_mean is not None else 'NULL'})."
            )

        result.rows.append(
            {
                "fecHora": hour_utc,
                "precioMarginalES": es_mean,
                "precioMarginalPT": pt_mean,
                "tipMercado": "diario",
            }
        )
        valid_hours.append(hour_utc)

    result.utc_hours = valid_hours
    return result


def transform_open_meteo(
    data: Dict[str, Any],
    ref_lat: float = 40.4176,
    ref_lon: float = -3.7394,
    coord_tolerance: float = 0.5,
) -> TransformResult:
    """
    Transforma el JSON columnar de Open-Meteo a filas horarias UTC para Meteorologia.
    Comprueba proximidad a Madrid (<= 0.5°) y desambigua horas repetidas de octubre.
    """
    result = TransformResult(source=SOURCE_OPEN_METEO, target_table="Meteorologia")
    if not isinstance(data, dict):
        result.warnings.append("JSON Open-Meteo inválido.")
        return result

    lat = _parse_finite_float(data.get("latitude"))
    lon = _parse_finite_float(data.get("longitude"))
    if lat is None or lon is None:
        result.warnings.append("Open-Meteo sin latitude/longitude válidos; no se escriben filas.")
        return result

    if abs(lat - ref_lat) > coord_tolerance or abs(lon - ref_lon) > coord_tolerance:
        result.warnings.append(
            f"Coordenadas Open-Meteo ({lat}, {lon}) alejadas más de {coord_tolerance}° de Madrid ({ref_lat}, {ref_lon}); escritura omitida."
        )
        return result

    tz_name = data.get("timezone")
    if not isinstance(tz_name, str) or not tz_name.strip():
        result.warnings.append("Open-Meteo sin campo 'timezone'; no se escriben filas.")
        return result
    try:
        local_tz = ZoneInfo(tz_name.strip())
    except ZoneInfoNotFoundError:
        result.warnings.append(f"Zona horaria Open-Meteo desconocida: '{tz_name}'; no se escriben filas.")
        return result

    hourly = data.get("hourly")
    times = hourly.get("time") if isinstance(hourly, dict) else None
    if not isinstance(times, list) or not times:
        result.warnings.append("Open-Meteo sin lista 'hourly.time'.")
        return result

    prev_utc: Optional[datetime] = None
    seen_naive_counts: Dict[datetime, int] = {}
    seen_utc_hours: set[datetime] = set()
    rows_by_hour: Dict[datetime, Dict[str, Any]] = {}
    invalid_time_count = 0
    invalid_value_warnings = 0

    for idx, time_raw in enumerate(times):
        if not isinstance(time_raw, str):
            invalid_time_count += 1
            continue
        text = time_raw.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt_parsed = datetime.fromisoformat(text)
        except ValueError:
            invalid_time_count += 1
            continue

        if dt_parsed.tzinfo is not None:
            dt_utc = dt_parsed.astimezone(timezone.utc)
        else:
            count = seen_naive_counts.get(dt_parsed, 0)
            seen_naive_counts[dt_parsed] = count + 1
            dt_fold0 = dt_parsed.replace(tzinfo=local_tz, fold=0).astimezone(timezone.utc)
            dt_fold1 = dt_parsed.replace(tzinfo=local_tz, fold=1).astimezone(timezone.utc)
            if dt_fold0 == dt_fold1:
                dt_utc = dt_fold0
            elif count == 0 and (prev_utc is None or dt_fold0 > prev_utc):
                dt_utc = dt_fold0
            else:
                dt_utc = dt_fold1

        prev_utc = dt_utc
        hour_utc = _truncate_utc_hour(dt_utc)

        if hour_utc in seen_utc_hours:
            result.warnings.append(
                f"Open-Meteo: hora UTC duplicada ignorada ({hour_utc.isoformat()}Z)."
            )
            continue
        seen_utc_hours.add(hour_utc)

        row: Dict[str, Any] = {"fecHora": hour_utc}
        has_any_metric = False

        def _get_val(key: str) -> Any:
            arr = hourly.get(key)
            if isinstance(arr, list) and idx < len(arr):
                return arr[idx]
            return None

        for src_key, col_name in OPEN_METEO_FLOAT_5_2_MAP.items():
            parsed, err = _parse_bounded_float(_get_val(src_key), -999.99, 999.99, 2)
            if err is not None:
                invalid_value_warnings += 1
            if parsed is not None:
                has_any_metric = True
            row[col_name] = parsed

        for src_key, col_name in OPEN_METEO_DIR_5_2_MAP.items():
            parsed, err = _parse_bounded_float(_get_val(src_key), 0.0, 360.0, 2)
            if err is not None:
                invalid_value_warnings += 1
            if parsed is not None:
                has_any_metric = True
            row[col_name] = parsed

        for src_key, col_name in OPEN_METEO_FLOAT_8_2_MAP.items():
            parsed, err = _parse_bounded_float(_get_val(src_key), -999999.99, 999999.99, 2)
            if err is not None:
                invalid_value_warnings += 1
            if parsed is not None:
                has_any_metric = True
            row[col_name] = parsed

        for src_key, col_name in OPEN_METEO_PCT_INT_MAP.items():
            parsed_int, err = _parse_bounded_int(_get_val(src_key), 0, 100)
            if err is not None:
                invalid_value_warnings += 1
            if parsed_int is not None:
                has_any_metric = True
            row[col_name] = parsed_int

        if has_any_metric:
            rows_by_hour[hour_utc] = row
        else:
            result.discarded_hours.append(
                {
                    "fec_hora_utc": hour_utc.isoformat() + "Z",
                    "reason": "Sin variables meteorológicas válidas",
                }
            )

    if invalid_time_count:
        result.warnings.append(f"Open-Meteo: {invalid_time_count} marcas de tiempo inválidas omitidas.")
    if invalid_value_warnings:
        result.warnings.append(
            f"Open-Meteo: {invalid_value_warnings} valores fuera de rango o no numéricos dejados en NULL."
        )

    sorted_hours = sorted(rows_by_hour.keys())
    result.utc_hours = sorted_hours
    result.rows = [rows_by_hour[hr] for hr in sorted_hours]
    return result


def transform_json_payload(
    data: Dict[str, Any],
    source: Optional[str] = None,
    config: Optional[OracleConfig] = None,
) -> TransformResult:
    """Autodetecta (si source es None) y ejecuta el transformador correspondiente."""
    cfg = config or OracleConfig.from_env()
    resolved_source = source or detect_source(data)

    if resolved_source == SOURCE_REE:
        return transform_ree(data, min_mw=cfg.ree_min_mw, max_mw=cfg.ree_max_mw)
    if resolved_source == SOURCE_OMIE:
        return transform_omie(
            data,
            min_price=cfg.omie_min_price,
            max_price=cfg.omie_max_price,
        )
    if resolved_source == SOURCE_OPEN_METEO:
        return transform_open_meteo(
            data,
            ref_lat=cfg.meteo_ref_lat,
            ref_lon=cfg.meteo_ref_lon,
            coord_tolerance=cfg.meteo_coord_tolerance,
        )
    raise ValueError(f"Fuente no soportada para Oracle: {resolved_source}")

