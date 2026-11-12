"""
Punto de entrada principal de persistencia Oracle y modo dry-run.
Orquesta validación, transacción única por fuente, reintentos ORA-00001 / ORA-00060
y tolerancia total a fallos sin propagar excepciones al flujo de ingesta.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import json
import logging
import time

from oracle_store.config import OracleConfig
from oracle_store.connection import (
    OracleConnectionError,
    SchemaValidationError,
    connect_oracle,
    extract_oracle_error_code,
    verify_schema,
)
from oracle_store.repository import (
    get_ccaa_id,
    merge_meteo_rows,
    merge_omie_rows,
    merge_ree_rows,
)
from oracle_store.time_dimension import ensure_tiempo_horario
from oracle_store.transformers import (
    SOURCE_OMIE,
    SOURCE_OPEN_METEO,
    SOURCE_REE,
    TransformResult,
    transform_json_payload,
)

logger = logging.getLogger("EcoGrid.Oracle")

RETRYABLE_TRANSACTION_CODES = {1, 60}  # ORA-00001 (unique), ORA-00060 (deadlock)


@dataclass
class DryRunReport:
    """Resumen de simulación sin conexión a base de datos."""

    source: str
    target_table: str
    tiempo_horario_rows: int
    fact_rows: int
    first_utc: Optional[str]
    last_utc: Optional[str]
    partial_hours_discarded: List[Dict[str, Any]] = field(default_factory=list)
    partial_series_nulls: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PersistResult:
    """Resultado de persist_to_oracle con detalle de filas insertadas y actualizadas."""

    executed: bool
    skipped: bool
    source: str
    target_table: str = ""
    rows_merged: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    tiempo_rows_ensured: int = 0
    tiempo_rows_inserted: int = 0
    tiempo_rows_existing: int = 0
    connection_info: Optional[str] = None
    reason: Optional[str] = None


def _load_json_file(json_path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(json_path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"El archivo {path.name} no contiene un objeto JSON raíz.")
    return data


def _log_transform_warnings(source: str, result: TransformResult) -> None:
    for warning in result.warnings:
        logger.warning("Transformación %s: %s", source, warning)


def dry_run_file(
    json_path: Union[str, Path],
    source: Optional[str] = None,
    config: Optional[OracleConfig] = None,
) -> DryRunReport:
    """
    Transforma un JSON y genera el reporte de filas por tabla sin abrir conexión Oracle.
    """
    cfg = config or OracleConfig.from_env()
    data = _load_json_file(json_path)
    transformed = transform_json_payload(data, source=source, config=cfg)
    return DryRunReport(
        source=transformed.source,
        target_table=transformed.target_table,
        tiempo_horario_rows=len(transformed.utc_hours),
        fact_rows=len(transformed.rows),
        first_utc=transformed.first_utc.isoformat() + "Z" if transformed.first_utc else None,
        last_utc=transformed.last_utc.isoformat() + "Z" if transformed.last_utc else None,
        partial_hours_discarded=transformed.discarded_hours,
        partial_series_nulls=transformed.partial_series,
        warnings=transformed.warnings,
    )


def _persist_transformed_with_connection(
    connection: Any,
    transformed: TransformResult,
    config: OracleConfig,
) -> PersistResult:
    calendar_tz = config.calendar_tz

    with connection.cursor() as cursor:
        id_tiempo_map = ensure_tiempo_horario(cursor, transformed.utc_hours, calendar_tz)
        t_inserted = getattr(id_tiempo_map, "inserted", 0)
        t_existing = getattr(id_tiempo_map, "existing", len(id_tiempo_map) - t_inserted)

        if transformed.source == SOURCE_REE:
            id_ccaa = get_ccaa_id(cursor, config.nacional_ccaa_codine)
            stats = merge_ree_rows(cursor, transformed.rows, id_ccaa, id_tiempo_map)
        elif transformed.source == SOURCE_OMIE:
            stats = merge_omie_rows(cursor, transformed.rows, id_tiempo_map)
        elif transformed.source == SOURCE_OPEN_METEO:
            id_ccaa = get_ccaa_id(cursor, config.meteo_ccaa_codine)
            stats = merge_meteo_rows(cursor, transformed.rows, id_ccaa, id_tiempo_map)
        else:
            raise ValueError(f"Fuente no soportada: {transformed.source}")

    connection.commit()
    conn_info = f"usuario={config.user}, dsn={config.dsn}"
    return PersistResult(
        executed=True,
        skipped=False,
        source=transformed.source,
        target_table=transformed.target_table,
        rows_merged=int(stats),
        rows_inserted=getattr(stats, "inserted", 0),
        rows_updated=getattr(stats, "updated", 0),
        tiempo_rows_ensured=len(id_tiempo_map),
        tiempo_rows_inserted=t_inserted,
        tiempo_rows_existing=t_existing,
        connection_info=conn_info,
    )


def persist_to_oracle(
    source: Optional[str],
    json_path: Union[str, Path],
    config: Optional[OracleConfig] = None,
    connector_fn: Optional[Callable[[OracleConfig], Any]] = None,
    max_tx_attempts: int = 3,
    tx_retry_delay_seconds: float = 0.2,
    raise_on_error: bool = False,
) -> PersistResult:
    """
    Persiste un JSON ya guardado en Oracle dentro de una única transacción por fuente.
    Si raise_on_error=False, nunca propaga excepciones al flujo de ingesta.
    Si raise_on_error=True (modo explícito para backfill o CLI), propaga los errores para mayor visibilidad.
    """
    source_label = source or "auto"
    try:
        cfg = config or OracleConfig.from_env()
        issue = cfg.readiness_issue()
        if issue is not None:
            logger.warning("Persistencia Oracle omitida (%s): %s.", source_label, issue)
            if raise_on_error:
                raise RuntimeError(f"Persistencia Oracle no lista ({source_label}): {issue}")
            return PersistResult(
                executed=False,
                skipped=True,
                source=source_label,
                reason=issue,
            )

        data = _load_json_file(json_path)
        transformed = transform_json_payload(data, source=source, config=cfg)
        source_label = transformed.source
        _log_transform_warnings(source_label, transformed)

        if not transformed.rows:
            reason = "no hay filas válidas para persistir"
            logger.warning(
                "Persistencia Oracle omitida (%s -> %s): %s.",
                source_label,
                transformed.target_table,
                reason,
            )
            if raise_on_error:
                raise ValueError(
                    f"No hay filas válidas para persistir en {transformed.target_table} ({source_label})."
                )
            return PersistResult(
                executed=False,
                skipped=True,
                source=source_label,
                target_table=transformed.target_table,
                reason=reason,
            )

        # Validar timezone antes de conectar
        _ = cfg.calendar_tz

        connect_callable = connector_fn or connect_oracle
        connection = connect_callable(cfg)
        try:
            verify_schema(connection, cfg)

            for attempt in range(1, max_tx_attempts + 1):
                try:
                    res = _persist_transformed_with_connection(connection, transformed, cfg)
                    logger.info(
                        "Persistencia Oracle completada (%s -> %s): %s filas merged (%s insertadas, %s actualizadas), %s horas en TiempoHorario (%s insertadas, %s existentes) (usuario=%s, dsn=%s).",
                        res.source,
                        res.target_table,
                        res.rows_merged,
                        res.rows_inserted,
                        res.rows_updated,
                        res.tiempo_rows_ensured,
                        res.tiempo_rows_inserted,
                        res.tiempo_rows_existing,
                        cfg.user,
                        cfg.dsn,
                    )
                    return res
                except Exception as tx_exc:
                    try:
                        connection.rollback()
                    except Exception:
                        pass

                    ora_code = extract_oracle_error_code(tx_exc)
                    if ora_code in RETRYABLE_TRANSACTION_CODES and attempt < max_tx_attempts:
                        logger.warning(
                            "Reintentando transacción Oracle (%s) tras ORA-%05d (intento %s/%s).",
                            source_label,
                            ora_code,
                            attempt,
                            max_tx_attempts,
                        )
                        time.sleep(tx_retry_delay_seconds * attempt)
                        continue

                    logger.error(
                        "Error en transacción Oracle (%s -> %s, usuario=%s, dsn=%s): %s",
                        source_label,
                        transformed.target_table,
                        cfg.user,
                        cfg.dsn,
                        tx_exc,
                    )
                    if raise_on_error:
                        raise tx_exc
                    return PersistResult(
                        executed=False,
                        skipped=False,
                        source=source_label,
                        target_table=transformed.target_table,
                        reason=str(tx_exc),
                    )
        finally:
            try:
                connection.close()
            except Exception:
                pass

    except (OracleConnectionError, SchemaValidationError) as exc:
        logger.error("Persistencia Oracle abortada (%s): %s", source_label, exc)
        if raise_on_error:
            raise exc
        return PersistResult(
            executed=False,
            skipped=False,
            source=source_label,
            reason=str(exc),
        )
    except Exception as exc:
        logger.error("Error inesperado en persist_to_oracle (%s): %s", source_label, exc)
        if raise_on_error:
            raise exc
        return PersistResult(
            executed=False,
            skipped=False,
            source=source_label,
            reason=str(exc),
        )

