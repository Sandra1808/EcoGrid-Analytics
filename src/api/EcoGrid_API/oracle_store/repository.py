"""
Repositorio SQL idempotente (MERGE) para las tablas de hechos y lectura de ComunidadAutonoma.
Todas las consultas usan variables bind sin concatenar datos.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Set

from oracle_store.connection import set_cursor_inputsizes


@dataclass
class MergeStats:
    """Estadísticas de la operación MERGE (total procesadas, insertadas y actualizadas)."""

    total: int
    inserted: int
    updated: int

    def __int__(self) -> int:
        return self.total

    def __index__(self) -> int:
        return self.total

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, int):
            return self.total == other
        if isinstance(other, MergeStats):
            return (self.total, self.inserted, self.updated) == (
                other.total,
                other.inserted,
                other.updated,
            )
        return False

SELECT_CCAA_ID_SQL = """
SELECT idCCAA
FROM ComunidadAutonoma
WHERE codIne = :cod_ine
"""

MERGE_REE_SQL = """
MERGE INTO DemandaGeneracionREE tgt
USING (
    SELECT
        :idTiempo AS idTiempo,
        :idCCAA AS idCCAA,
        :demandaRealMW AS demandaRealMW,
        :demandaPrevistaREEMW AS demandaPrevistaREEMW,
        :demandaProgramadaMW AS demandaProgramadaMW,
        :demandaProgramadaTotalMW AS demandaProgramadaTotalMW
    FROM DUAL
) src
ON (tgt.idTiempo = src.idTiempo AND tgt.idCCAA = src.idCCAA)
WHEN MATCHED THEN
    UPDATE SET
        tgt.demandaRealMW = COALESCE(src.demandaRealMW, tgt.demandaRealMW),
        tgt.demandaPrevistaREEMW = COALESCE(src.demandaPrevistaREEMW, tgt.demandaPrevistaREEMW),
        tgt.demandaProgramadaMW = COALESCE(src.demandaProgramadaMW, tgt.demandaProgramadaMW),
        tgt.demandaProgramadaTotalMW = COALESCE(src.demandaProgramadaTotalMW, tgt.demandaProgramadaTotalMW)
WHEN NOT MATCHED THEN
    INSERT (
        idTiempo,
        idCCAA,
        demandaRealMW,
        demandaPrevistaREEMW,
        demandaProgramadaMW,
        demandaProgramadaTotalMW
    )
    VALUES (
        src.idTiempo,
        src.idCCAA,
        src.demandaRealMW,
        src.demandaPrevistaREEMW,
        src.demandaProgramadaMW,
        src.demandaProgramadaTotalMW
    )
"""

MERGE_OMIE_SQL = """
MERGE INTO PreciosMercadoOmie tgt
USING (
    SELECT
        :idTiempo AS idTiempo,
        :precioMarginalES AS precioMarginalES,
        :precioMarginalPT AS precioMarginalPT,
        :tipMercado AS tipMercado
    FROM DUAL
) src
ON (tgt.idTiempo = src.idTiempo AND tgt.tipMercado = src.tipMercado)
WHEN MATCHED THEN
    UPDATE SET
        tgt.precioMarginalES = COALESCE(src.precioMarginalES, tgt.precioMarginalES),
        tgt.precioMarginalPT = COALESCE(src.precioMarginalPT, tgt.precioMarginalPT)
WHEN NOT MATCHED THEN
    INSERT (
        idTiempo,
        precioMarginalES,
        precioMarginalPT,
        tipMercado
    )
    VALUES (
        src.idTiempo,
        src.precioMarginalES,
        src.precioMarginalPT,
        src.tipMercado
    )
"""

MERGE_METEO_SQL = """
MERGE INTO Meteorologia tgt
USING (
    SELECT
        :idTiempo AS idTiempo,
        :idCCAA AS idCCAA,
        :temperatura_2m AS temperatura_2m,
        :viento_10m AS viento_10m,
        :viento_80m AS viento_80m,
        :viento_120m AS viento_120m,
        :viento_180m AS viento_180m,
        :viento_dir_10m AS viento_dir_10m,
        :viento_dir_80m AS viento_dir_80m,
        :viento_dir_120m AS viento_dir_120m,
        :viento_dir_180m AS viento_dir_180m,
        :radiacion_directa AS radiacion_directa,
        :shortwave_radiation AS shortwave_radiation,
        :global_tilted_irradiance AS global_tilted_irradiance,
        :cobertura_nubes AS cobertura_nubes,
        :humedad_relativa AS humedad_relativa
    FROM DUAL
) src
ON (tgt.idTiempo = src.idTiempo AND tgt.idCCAA = src.idCCAA)
WHEN MATCHED THEN
    UPDATE SET
        tgt.temperatura_2m = COALESCE(src.temperatura_2m, tgt.temperatura_2m),
        tgt.viento_10m = COALESCE(src.viento_10m, tgt.viento_10m),
        tgt.viento_80m = COALESCE(src.viento_80m, tgt.viento_80m),
        tgt.viento_120m = COALESCE(src.viento_120m, tgt.viento_120m),
        tgt.viento_180m = COALESCE(src.viento_180m, tgt.viento_180m),
        tgt.viento_dir_10m = COALESCE(src.viento_dir_10m, tgt.viento_dir_10m),
        tgt.viento_dir_80m = COALESCE(src.viento_dir_80m, tgt.viento_dir_80m),
        tgt.viento_dir_120m = COALESCE(src.viento_dir_120m, tgt.viento_dir_120m),
        tgt.viento_dir_180m = COALESCE(src.viento_dir_180m, tgt.viento_dir_180m),
        tgt.radiacion_directa = COALESCE(src.radiacion_directa, tgt.radiacion_directa),
        tgt.shortwave_radiation = COALESCE(src.shortwave_radiation, tgt.shortwave_radiation),
        tgt.global_tilted_irradiance = COALESCE(src.global_tilted_irradiance, tgt.global_tilted_irradiance),
        tgt.cobertura_nubes = COALESCE(src.cobertura_nubes, tgt.cobertura_nubes),
        tgt.humedad_relativa = COALESCE(src.humedad_relativa, tgt.humedad_relativa)
WHEN NOT MATCHED THEN
    INSERT (
        idTiempo,
        idCCAA,
        temperatura_2m,
        viento_10m,
        viento_80m,
        viento_120m,
        viento_180m,
        viento_dir_10m,
        viento_dir_80m,
        viento_dir_120m,
        viento_dir_180m,
        radiacion_directa,
        shortwave_radiation,
        global_tilted_irradiance,
        cobertura_nubes,
        humedad_relativa
    )
    VALUES (
        src.idTiempo,
        src.idCCAA,
        src.temperatura_2m,
        src.viento_10m,
        src.viento_80m,
        src.viento_120m,
        src.viento_180m,
        src.viento_dir_10m,
        src.viento_dir_80m,
        src.viento_dir_120m,
        src.viento_dir_180m,
        src.radiacion_directa,
        src.shortwave_radiation,
        src.global_tilted_irradiance,
        src.cobertura_nubes,
        src.humedad_relativa
    )
"""


def get_ccaa_id(cursor: Any, cod_ine: str) -> int:
    """Obtiene idCCAA desde ComunidadAutonoma usando codIne."""
    cursor.execute(SELECT_CCAA_ID_SQL, {"cod_ine": cod_ine})
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No existe ComunidadAutonoma con codIne='{cod_ine}'.")
    return int(row[0])


def merge_ree_rows(
    cursor: Any,
    rows: List[Dict[str, Any]],
    id_ccaa: int,
    id_tiempo_map: Dict[datetime, int],
) -> MergeStats:
    """Ejecuta MERGE por lotes en DemandaGeneracionREE."""
    if not rows:
        return MergeStats(total=0, inserted=0, updated=0)
    payload = [
        {
            "idTiempo": id_tiempo_map[r["fecHora"]],
            "idCCAA": id_ccaa,
            "demandaRealMW": r["demandaRealMW"],
            "demandaPrevistaREEMW": r["demandaPrevistaREEMW"],
            "demandaProgramadaMW": r["demandaProgramadaMW"],
            "demandaProgramadaTotalMW": r["demandaProgramadaTotalMW"],
        }
        for r in rows
    ]
    ids = [p["idTiempo"] for p in payload]
    existing_ids: Set[int] = set()
    try:
        min_id = min(ids)
        max_id = max(ids)
        cursor.execute(
            "SELECT idTiempo FROM DemandaGeneracionREE WHERE idCCAA = :id_ccaa AND idTiempo BETWEEN :min_id AND :max_id",
            {"id_ccaa": id_ccaa, "min_id": min_id, "max_id": max_id},
        )
        existing_ids = {int(row[0]) for row in cursor.fetchall()}
    except Exception:
        existing_ids = set()

    updated_count = sum(1 for p in payload if p["idTiempo"] in existing_ids)
    inserted_count = len(payload) - updated_count

    set_cursor_inputsizes(
        cursor,
        idTiempo="NUMBER",
        idCCAA="NUMBER",
        demandaRealMW="NUMBER",
        demandaPrevistaREEMW="NUMBER",
        demandaProgramadaMW="NUMBER",
        demandaProgramadaTotalMW="NUMBER",
    )
    cursor.executemany(MERGE_REE_SQL, payload)
    return MergeStats(total=len(payload), inserted=inserted_count, updated=updated_count)


def merge_omie_rows(
    cursor: Any,
    rows: List[Dict[str, Any]],
    id_tiempo_map: Dict[datetime, int],
) -> MergeStats:
    """Ejecuta MERGE por lotes en PreciosMercadoOmie."""
    if not rows:
        return MergeStats(total=0, inserted=0, updated=0)
    payload = [
        {
            "idTiempo": id_tiempo_map[r["fecHora"]],
            "precioMarginalES": r["precioMarginalES"],
            "precioMarginalPT": r["precioMarginalPT"],
            "tipMercado": r["tipMercado"],
        }
        for r in rows
    ]
    ids = [p["idTiempo"] for p in payload]
    existing_ids: Set[int] = set()
    try:
        min_id = min(ids)
        max_id = max(ids)
        cursor.execute(
            "SELECT idTiempo FROM PreciosMercadoOmie WHERE tipMercado = :tip AND idTiempo BETWEEN :min_id AND :max_id",
            {"tip": "diario", "min_id": min_id, "max_id": max_id},
        )
        existing_ids = {int(row[0]) for row in cursor.fetchall()}
    except Exception:
        existing_ids = set()

    updated_count = sum(1 for p in payload if p["idTiempo"] in existing_ids)
    inserted_count = len(payload) - updated_count

    set_cursor_inputsizes(
        cursor,
        idTiempo="NUMBER",
        precioMarginalES="NUMBER",
        precioMarginalPT="NUMBER",
        tipMercado="VARCHAR",
    )
    cursor.executemany(MERGE_OMIE_SQL, payload)
    return MergeStats(total=len(payload), inserted=inserted_count, updated=updated_count)


def merge_meteo_rows(
    cursor: Any,
    rows: List[Dict[str, Any]],
    id_ccaa: int,
    id_tiempo_map: Dict[datetime, int],
) -> MergeStats:
    """Ejecuta MERGE por lotes en Meteorologia (sin incluir temperaturaAparente)."""
    if not rows:
        return MergeStats(total=0, inserted=0, updated=0)
    payload = [
        {
            "idTiempo": id_tiempo_map[r["fecHora"]],
            "idCCAA": id_ccaa,
            "temperatura_2m": r["temperatura_2m"],
            "viento_10m": r["viento_10m"],
            "viento_80m": r["viento_80m"],
            "viento_120m": r["viento_120m"],
            "viento_180m": r["viento_180m"],
            "viento_dir_10m": r["viento_dir_10m"],
            "viento_dir_80m": r["viento_dir_80m"],
            "viento_dir_120m": r["viento_dir_120m"],
            "viento_dir_180m": r["viento_dir_180m"],
            "radiacion_directa": r["radiacion_directa"],
            "shortwave_radiation": r["shortwave_radiation"],
            "global_tilted_irradiance": r["global_tilted_irradiance"],
            "cobertura_nubes": r["cobertura_nubes"],
            "humedad_relativa": r["humedad_relativa"],
        }
        for r in rows
    ]
    ids = [p["idTiempo"] for p in payload]
    existing_ids: Set[int] = set()
    try:
        min_id = min(ids)
        max_id = max(ids)
        cursor.execute(
            "SELECT idTiempo FROM Meteorologia WHERE idCCAA = :id_ccaa AND idTiempo BETWEEN :min_id AND :max_id",
            {"id_ccaa": id_ccaa, "min_id": min_id, "max_id": max_id},
        )
        existing_ids = {int(row[0]) for row in cursor.fetchall()}
    except Exception:
        existing_ids = set()

    updated_count = sum(1 for p in payload if p["idTiempo"] in existing_ids)
    inserted_count = len(payload) - updated_count

    set_cursor_inputsizes(
        cursor,
        idTiempo="NUMBER",
        idCCAA="NUMBER",
        temperatura_2m="NUMBER",
        viento_10m="NUMBER",
        viento_80m="NUMBER",
        viento_120m="NUMBER",
        viento_180m="NUMBER",
        viento_dir_10m="NUMBER",
        viento_dir_80m="NUMBER",
        viento_dir_120m="NUMBER",
        viento_dir_180m="NUMBER",
        radiacion_directa="NUMBER",
        shortwave_radiation="NUMBER",
        global_tilted_irradiance="NUMBER",
        cobertura_nubes="NUMBER",
        humedad_relativa="NUMBER",
    )
    cursor.executemany(MERGE_METEO_SQL, payload)
    return MergeStats(total=len(payload), inserted=inserted_count, updated=updated_count)

