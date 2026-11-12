"""
Suite de tests sin base de datos Oracle para oracle_store e integración mínima en IngestionService.
Cubre:
- Transformadores puros con los 3 JSON de referencia y criterios de la sección 11.
- Casos de cambio horario (92/100 periodos OMIE, offset variable REE, hora repetida Open-Meteo).
- Dimensión TiempoHorario (192 filas totales, calendario Europe/Madrid, FestivosBOE).
- Guarda de esquema, idempotencia, COALESCE, reintentos ORA-00001 con BBDD en memoria simulada.
- Modo CLI --dry-run sin abrir conexión.
- Comportamiento inalterado de IngestionService con ORACLE_ENABLED=false o fallo Oracle.
"""

from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch
from zoneinfo import ZoneInfo
import io
import json
import os
import sys
import unittest

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store import cli, persist_to_oracle
from oracle_store.config import OracleConfig
from oracle_store.connection import (
    REQUIRED_SCHEMA_COLUMNS,
    OracleConnectionError,
    connect_oracle,
    oracledb,
    reset_schema_cache,
)
from oracle_store.time_dimension import build_tiempo_horario_row, compute_id_tiempo
from oracle_store.transformers import (
    SOURCE_OMIE,
    SOURCE_OPEN_METEO,
    SOURCE_REE,
    detect_source,
    transform_omie,
    transform_open_meteo,
    transform_ree,
)
from src.services.ingestion_service import IngestionService

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REE_FIXTURE = FIXTURES_DIR / "ree_esios_20261028_162855.json"
OMIE_FIXTURE = FIXTURES_DIR / "omie_20261028_162854.json"
METEO_FIXTURE = FIXTURES_DIR / "open_meteo_20261028_162853.json"
DDL_FIXTURE = FIXTURES_DIR / "crearTablasBBDDEcoGrid_v3.sql"


def _load_fixture(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class FakeOracleError(Exception):
    """Simula una excepción DatabaseError de oracledb con código ORA-XXXXX."""

    def __init__(self, code: int, message: str):
        self.code = code
        super().__init__(f"ORA-{code:05d}: {message}")


class FakeCursor:
    """Cursor en memoria para verificar SQL, binds, guarda de esquema, COALESCE e idempotencia."""

    def __init__(self, db: "FakeOracleDB"):
        self.db = db
        self._results: List[Tuple[Any, ...]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def setinputsizes(self, **kwargs: Any) -> None:
        self.db.last_inputsizes = kwargs

    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> None:
        params = params or {}
        norm = " ".join(sql.split()).upper()

        if "FROM USER_TAB_COLUMNS" in norm:
            rows = []
            for table, cols in self.db.schema_columns.items():
                for col in cols:
                    rows.append((table, col))
            self._results = rows
            return

        if "FROM COMUNIDADAUTONOMA" in norm and "WHERE CODINE IN" in norm:
            wanted = {params["cod_nacional"], params["cod_meteo"]}
            self._results = [
                (cod,) for cod in self.db.ccaa_by_codine if cod in wanted
            ]
            return

        if "FROM COMUNIDADAUTONOMA" in norm and "WHERE CODINE =" in norm:
            cod = params["cod_ine"]
            if cod in self.db.ccaa_by_codine:
                self._results = [(self.db.ccaa_by_codine[cod],)]
            else:
                self._results = []
            return

        if "FROM TIEMPOHORARIO" in norm and "BETWEEN" in norm:
            desde = params["desde"]
            hasta = params["hasta"]
            self._results = [
                (row["idTiempo"], row["fecHora"])
                for row in self.db.pending_tiempo.values()
                if desde <= row["fecHora"] <= hasta
            ]
            return

        if "FROM FESTIVOSBOE" in norm:
            f_desde = params["fecha_desde"]
            f_hasta = params["fecha_hasta"]
            self._results = [
                (d,) for d in self.db.national_holidays if f_desde <= d <= f_hasta
            ]
            return

        raise AssertionError(f"SQL inesperado en FakeCursor.execute: {sql}")

    def executemany(self, sql: str, rows: List[Dict[str, Any]]) -> None:
        norm = " ".join(sql.split()).upper()

        if norm.startswith("INSERT INTO TIEMPOHORARIO"):
            if self.db.fail_next_tiempo_insert_ora00001:
                self.db.fail_next_tiempo_insert_ora00001 = False
                # Simula que otra sesión concurrente ya insertó las filas y las confirmó
                for r in rows:
                    self.db.committed_tiempo[r["fecHora"]] = dict(r)
                self.db.pending_tiempo = {
                    k: dict(v) for k, v in self.db.committed_tiempo.items()
                }
                raise FakeOracleError(1, "unique constraint (UK_TIEMPO_FEC_HORA) violated")

            for r in rows:
                fec_hora = r["fecHora"]
                if fec_hora in self.db.pending_tiempo:
                    raise FakeOracleError(1, "unique constraint (UK_TIEMPO_FEC_HORA) violated")
                self.db.pending_tiempo[fec_hora] = dict(r)
            return

        if norm.startswith("MERGE INTO DEMANDAGENERACIONREE"):
            for r in rows:
                key = (r["idTiempo"], r["idCCAA"])
                current = self.db.pending_ree.get(key)
                if current is None:
                    self.db.pending_ree[key] = dict(r)
                else:
                    for col in (
                        "demandaRealMW",
                        "demandaPrevistaREEMW",
                        "demandaProgramadaMW",
                        "demandaProgramadaTotalMW",
                    ):
                        if r[col] is not None:
                            current[col] = r[col]
            return

        if norm.startswith("MERGE INTO PRECIOSMERCADOOMIE"):
            for r in rows:
                key = (r["idTiempo"], r["tipMercado"])
                current = self.db.pending_omie.get(key)
                if current is None:
                    self.db.pending_omie[key] = dict(r)
                else:
                    for col in ("precioMarginalES", "precioMarginalPT"):
                        if r[col] is not None:
                            current[col] = r[col]
            return

        if norm.startswith("MERGE INTO METEOROLOGIA"):
            for r in rows:
                key = (r["idTiempo"], r["idCCAA"])
                current = self.db.pending_meteo.get(key)
                if current is None:
                    self.db.pending_meteo[key] = dict(r)
                else:
                    for col, val in r.items():
                        if col not in ("idTiempo", "idCCAA") and val is not None:
                            current[col] = val
            return

        raise AssertionError(f"SQL inesperado en FakeCursor.executemany: {sql}")

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return list(self._results)

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        return self._results[0] if self._results else None


class FakeConnection:
    """Conexión simulada que gestiona commit y rollback."""

    def __init__(self, db: "FakeOracleDB"):
        self.db = db
        self.autocommit = True
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.db)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def close(self) -> None:
        self.closed = True


class FakeOracleDB:
    """Estado transaccional simulado de las tablas Oracle implicadas."""

    def __init__(self) -> None:
        self.schema_columns: Dict[str, set] = {
            t: set(cols) for t, cols in REQUIRED_SCHEMA_COLUMNS.items()
        }
        self.ccaa_by_codine: Dict[str, int] = {"00": 1, "13": 14}
        self.national_holidays: set[date] = set()
        self.committed_tiempo: Dict[datetime, Dict[str, Any]] = {}
        self.committed_ree: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.committed_omie: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.committed_meteo: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.pending_tiempo: Dict[datetime, Dict[str, Any]] = {}
        self.pending_ree: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.pending_omie: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.pending_meteo: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.fail_next_tiempo_insert_ora00001 = False
        self.last_inputsizes: Dict[str, Any] = {}
        self.connect_calls = 0

    def connect(self, _cfg: OracleConfig) -> FakeConnection:
        self.connect_calls += 1
        self.rollback()
        return FakeConnection(self)

    def commit(self) -> None:
        self.committed_tiempo = {k: dict(v) for k, v in self.pending_tiempo.items()}
        self.committed_ree = {k: dict(v) for k, v in self.pending_ree.items()}
        self.committed_omie = {k: dict(v) for k, v in self.pending_omie.items()}
        self.committed_meteo = {k: dict(v) for k, v in self.pending_meteo.items()}

    def rollback(self) -> None:
        self.pending_tiempo = {k: dict(v) for k, v in self.committed_tiempo.items()}
        self.pending_ree = {k: dict(v) for k, v in self.committed_ree.items()}
        self.pending_omie = {k: dict(v) for k, v in self.committed_omie.items()}
        self.pending_meteo = {k: dict(v) for k, v in self.committed_meteo.items()}


class TestReferenceFixtures(unittest.TestCase):
    """Validación contra los 3 JSON de referencia y criterios de sección 11."""

    def test_fixtures_exist(self) -> None:
        for path in (REE_FIXTURE, OMIE_FIXTURE, METEO_FIXTURE, DDL_FIXTURE):
            self.assertTrue(path.is_file(), f"Falta fixture: {path}")

    def test_ree_reference_values(self) -> None:
        data = _load_fixture(REE_FIXTURE)
        self.assertEqual(detect_source(data), SOURCE_REE)

        res = transform_ree(data)
        self.assertEqual(res.target_table, "DemandaGeneracionREE")
        self.assertEqual(len(res.rows), 48)
        self.assertEqual(res.first_utc, datetime(2026, 10, 26, 23, 0))
        self.assertEqual(res.last_utc, datetime(2026, 10, 28, 22, 0))

        target_hour = datetime(2026, 10, 28, 15, 0)
        row_15 = next(r for r in res.rows if r["fecHora"] == target_hour)
        self.assertIsNone(row_15["demandaRealMW"])
        self.assertIsNotNone(row_15["demandaPrevistaREEMW"])
        self.assertIsNotNone(row_15["demandaProgramadaMW"])
        self.assertIsNotNone(row_15["demandaProgramadaTotalMW"])

        self.assertTrue(
            any(
                p["column"] == "demandaRealMW" and p["points"] == 5
                for p in res.partial_series
            )
        )
        for gen_col in (
            "genEolicaMW",
            "genSolarMW",
            "genHidraulicaMW",
            "genNuclearMW",
            "genCicloCombinadoMW",
        ):
            self.assertNotIn(gen_col, row_15)

    def test_omie_reference_values(self) -> None:
        data = _load_fixture(OMIE_FIXTURE)
        self.assertEqual(detect_source(data), SOURCE_OMIE)

        res = transform_omie(data)
        self.assertEqual(res.target_table, "PreciosMercadoOmie")
        self.assertEqual(len(res.rows), 24)
        self.assertEqual(res.first_utc, datetime(2026, 10, 27, 23, 0))
        self.assertEqual(res.last_utc, datetime(2026, 10, 28, 22, 0))
        self.assertTrue(all(r["tipMercado"] == "diario" for r in res.rows))

        diff_hours = [
            r["fecHora"]
            for r in res.rows
            if r["precioMarginalES"] != r["precioMarginalPT"]
        ]
        self.assertEqual(len(diff_hours), 4)
        self.assertTrue(all(hr.day == 28 and hr.month == 10 for hr in diff_hours))

    def test_open_meteo_reference_values(self) -> None:
        data = _load_fixture(METEO_FIXTURE)
        self.assertEqual(detect_source(data), SOURCE_OPEN_METEO)

        res = transform_open_meteo(data)
        self.assertEqual(res.target_table, "Meteorologia")
        self.assertEqual(len(res.rows), 168)
        self.assertEqual(res.first_utc, datetime(2026, 10, 27, 23, 0))
        self.assertEqual(res.last_utc, datetime(2026, 11, 3, 22, 0))

        first_row = res.rows[0]
        self.assertNotIn("temperaturaAparente", first_row)
        self.assertEqual(first_row["temperatura_2m"], 12.3)
        self.assertEqual(first_row["viento_10m"], 3.3)
        self.assertIsInstance(first_row["humedad_relativa"], int)
        self.assertIsInstance(first_row["cobertura_nubes"], int)

    def test_tiempo_horario_union_is_192_hours(self) -> None:
        ree_res = transform_ree(_load_fixture(REE_FIXTURE))
        omie_res = transform_omie(_load_fixture(OMIE_FIXTURE))
        meteo_res = transform_open_meteo(_load_fixture(METEO_FIXTURE))

        union_hours = sorted(
            set(ree_res.utc_hours) | set(omie_res.utc_hours) | set(meteo_res.utc_hours)
        )
        self.assertEqual(len(union_hours), 192)

        madrid_tz = ZoneInfo("Europe/Madrid")
        first_row = build_tiempo_horario_row(
            datetime(2026, 10, 27, 23, 0),
            madrid_tz,
            national_holidays=set(),
        )
        self.assertEqual(first_row["idTiempo"], 2026102723)
        self.assertEqual(first_row["fecha"], date(2026, 10, 28))
        self.assertEqual(first_row["hora"], 0)
        self.assertEqual(first_row["diaSemana"], 3)
        self.assertEqual(first_row["indFinSemana"], 0)
        self.assertEqual(first_row["indFestivo"], 0)

        holiday_row = build_tiempo_horario_row(
            datetime(2026, 11, 1, 10, 0),
            madrid_tz,
            national_holidays={date(2026, 11, 1)},
        )
        self.assertEqual(holiday_row["diaSemana"], 7)
        self.assertEqual(holiday_row["indFinSemana"], 1)
        self.assertEqual(holiday_row["indFestivo"], 1)


class TestDSTAndValidation(unittest.TestCase):
    """Tests sintéticos de cambio horario (DST), deduplicación y rangos."""

    def test_omie_dst_92_and_100_periods(self) -> None:
        # 2026-03-29: cambio de invierno -> verano (23 horas = 92 periodos)
        spring_records = [
            {
                "year": 2026,
                "month": 3,
                "day": 29,
                "hour": p,
                "price_spain": 50.0 + p * 0.1,
                "price_portugal": 50.0 + p * 0.1,
            }
            for p in range(1, 93)
        ]
        spring_res = transform_omie({"market": "OMIE", "records": spring_records})
        self.assertEqual(len(spring_res.rows), 23)
        self.assertEqual(spring_res.first_utc, datetime(2026, 3, 28, 23, 0))
        self.assertEqual(spring_res.last_utc, datetime(2026, 3, 29, 21, 0))

        # 2026-10-25: cambio de verano -> invierno (25 horas = 100 periodos)
        autumn_records = [
            {
                "year": 2026,
                "month": 10,
                "day": 25,
                "hour": p,
                "price_spain": 60.0 + p * 0.1,
                "price_portugal": 60.0 + p * 0.1,
            }
            for p in range(1, 101)
        ]
        autumn_res = transform_omie({"market": "OMIE", "records": autumn_records})
        self.assertEqual(len(autumn_res.rows), 25)
        self.assertEqual(autumn_res.first_utc, datetime(2026, 10, 24, 22, 0))
        self.assertEqual(autumn_res.last_utc, datetime(2026, 10, 25, 22, 0))

    def test_ree_variable_offset_dedup_and_range(self) -> None:
        # Cruce de cambio horario 2026-10-25 (+02:00 -> +01:00)
        values = []
        # 02:00+02:00 (00:00Z): 12 puntos + 1 duplicado exacto
        for m in range(0, 60, 5):
            values.append(
                {"value": 25000.0, "datetime": f"2026-10-25T02:{m:02d}:00.000+02:00"}
            )
        values.append({"value": 25000.0, "datetime": "2026-10-25T02:00:00.000+02:00"})

        # 02:00+01:00 (01:00Z): 12 puntos con uno fuera de rango -> queda parcial (NULL)
        for m in range(0, 60, 5):
            val = 99999.0 if m == 55 else 24000.0
            values.append(
                {"value": val, "datetime": f"2026-10-25T02:{m:02d}:00.000+01:00"}
            )

        # Prevista válida para ambas horas para que 01:00Z conserve fila
        prevista_vals = [
            {"value": 24500.0, "datetime": f"2026-10-25T02:{m:02d}:00.000+02:00"}
            for m in range(0, 60, 5)
        ] + [
            {"value": 24500.0, "datetime": f"2026-10-25T02:{m:02d}:00.000+01:00"}
            for m in range(0, 60, 5)
        ]

        ree_payload = {
            "api_origin": "apidatos.ree.es",
            "payload": {
                "included": [
                    {"type": "Real", "attributes": {"values": values}},
                    {"type": "Prevista", "attributes": {"values": prevista_vals}},
                ]
            },
        }
        res = transform_ree(ree_payload)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.rows[0]["fecHora"], datetime(2026, 10, 25, 0, 0))
        self.assertEqual(res.rows[0]["demandaRealMW"], 25000.0)
        self.assertEqual(res.rows[1]["fecHora"], datetime(2026, 10, 25, 1, 0))
        self.assertIsNone(res.rows[1]["demandaRealMW"])
        self.assertEqual(res.rows[1]["demandaPrevistaREEMW"], 24500.0)

    def test_open_meteo_dst_repeated_hour_fold_disambiguation(self) -> None:
        synthetic_meteo = {
            "latitude": 40.4176,
            "longitude": -3.7394,
            "timezone": "Europe/Madrid",
            "hourly": {
                "time": [
                    "2026-10-25T01:00",
                    "2026-10-25T02:00",  # fold=0 (+02:00) -> 00:00Z
                    "2026-10-25T02:00",  # fold=1 (+01:00) -> 01:00Z
                    "2026-10-25T03:00",
                ],
                "temperature_2m": [10.0, 11.0, 12.0, 13.0],
                "relative_humidity_2m": [70, 72, 74, 76],
                "cloud_cover": [10, 20, 30, 40],
            },
        }
        res = transform_open_meteo(synthetic_meteo)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(
            [r["fecHora"] for r in res.rows],
            [
                datetime(2026, 10, 24, 23, 0),
                datetime(2026, 10, 25, 0, 0),
                datetime(2026, 10, 25, 1, 0),
                datetime(2026, 10, 25, 2, 0),
            ],
        )
        self.assertEqual([r["temperatura_2m"] for r in res.rows], [10.0, 11.0, 12.0, 13.0])

    def test_open_meteo_coordinate_guard_and_omie_range_guard(self) -> None:
        far_meteo = {
            "latitude": 41.3851,
            "longitude": 2.1734,
            "timezone": "Europe/Madrid",
            "hourly": {"time": ["2026-10-28T00:00"], "temperature_2m": [15.0]},
        }
        res_far = transform_open_meteo(far_meteo)
        self.assertEqual(len(res_far.rows), 0)
        self.assertTrue(any("Madrid" in w for w in res_far.warnings))

        omie_partial = transform_omie(
            {
                "market": "OMIE",
                "records": [
                    # Hora 1: solo 3 periodos -> descartada
                    {"year": 2026, "month": 10, "day": 28, "hour": 1, "price_spain": 50.0, "price_portugal": 50.0},
                    {"year": 2026, "month": 10, "day": 28, "hour": 1, "price_spain": 50.0, "price_portugal": 50.0},
                    {"year": 2026, "month": 10, "day": 28, "hour": 1, "price_spain": 50.0, "price_portugal": 50.0},
                    # Hora 2: fuera de rango en ambos -> descartada
                    {"year": 2026, "month": 10, "day": 28, "hour": 5, "price_spain": 4500.0, "price_portugal": 4500.0},
                    {"year": 2026, "month": 10, "day": 28, "hour": 6, "price_spain": 50.0, "price_portugal": 50.0},
                    {"year": 2026, "month": 10, "day": 28, "hour": 7, "price_spain": 50.0, "price_portugal": 50.0},
                    {"year": 2026, "month": 10, "day": 28, "hour": 8, "price_spain": 50.0, "price_portugal": 50.0},
                    # Hora 3: ES válido, PT None -> se escribe con PT=NULL
                    {"year": 2026, "month": 10, "day": 28, "hour": 9, "price_spain": 100.0, "price_portugal": None},
                    {"year": 2026, "month": 10, "day": 28, "hour": 10, "price_spain": 100.0, "price_portugal": None},
                    {"year": 2026, "month": 10, "day": 28, "hour": 11, "price_spain": 100.0, "price_portugal": None},
                    {"year": 2026, "month": 10, "day": 28, "hour": 12, "price_spain": 100.0, "price_portugal": None},
                ],
            }
        )
        self.assertEqual(len(omie_partial.rows), 1)
        self.assertEqual(omie_partial.rows[0]["precioMarginalES"], 100.0)
        self.assertIsNone(omie_partial.rows[0]["precioMarginalPT"])
        self.assertEqual(len(omie_partial.discarded_hours), 2)


class TestPersistenceRepositoryAndIntegration(unittest.TestCase):
    """Tests de transacción simulada, guarda de esquema, CLI --dry-run e IngestionService."""

    def setUp(self) -> None:
        reset_schema_cache()

    def _make_config(self, wallet_dir: str) -> OracleConfig:
        return OracleConfig(
            enabled=True,
            user="ECOGRID",
            password="secret-in-test-only",
            dsn="ecogrid_low",
            wallet_dir=wallet_dir,
            wallet_password="wallet-secret-in-test-only",
            connect_timeout=20,
        )

    def test_end_to_end_mock_db_idempotency_coalesce_and_retry(self) -> None:
        db = FakeOracleDB()
        with TemporaryDirectory() as tmp_wallet:
            cfg = self._make_config(tmp_wallet)

            # Simula una fila previa creada por otro componente con idTiempo distinto
            preexisting_hr = datetime(2026, 10, 26, 23, 0)
            db.committed_tiempo[preexisting_hr] = {
                "idTiempo": 9999999999,
                "fecHora": preexisting_hr,
            }
            db.rollback()

            # Simula colisión ORA-00001 en el primer intento de REE
            db.fail_next_tiempo_insert_ora00001 = True

            r1 = persist_to_oracle(
                SOURCE_REE, REE_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )
            self.assertTrue(r1.executed)
            self.assertEqual(r1.rows_merged, 48)
            self.assertIn((9999999999, 1), db.committed_ree)

            # Persistir OMIE y Open-Meteo
            r2 = persist_to_oracle(
                SOURCE_OMIE, OMIE_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )
            r3 = persist_to_oracle(
                SOURCE_OPEN_METEO, METEO_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )
            self.assertTrue(r2.executed)
            self.assertEqual(r2.rows_merged, 24)
            self.assertTrue(r3.executed)
            self.assertEqual(r3.rows_merged, 168)
            self.assertEqual(len(db.committed_tiempo), 192)

            # Verificar COALESCE: rellenamos artificialmente 15:00Z real en BD y reingresamos mismo JSON parcial
            id_15z = compute_id_tiempo(datetime(2026, 10, 28, 15, 0))
            db.committed_ree[(id_15z, 1)]["demandaRealMW"] = 31234.5678
            db.rollback()

            snapshot_omie = dict(db.committed_omie)
            snapshot_meteo = dict(db.committed_meteo)

            persist_to_oracle(
                SOURCE_REE, REE_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )
            persist_to_oracle(
                SOURCE_OMIE, OMIE_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )
            persist_to_oracle(
                SOURCE_OPEN_METEO, METEO_FIXTURE, config=cfg, connector_fn=db.connect, tx_retry_delay_seconds=0.0
            )

            self.assertEqual(db.committed_ree[(id_15z, 1)]["demandaRealMW"], 31234.5678)
            self.assertEqual(len(db.committed_tiempo), 192)
            self.assertEqual(db.committed_omie, snapshot_omie)
            self.assertEqual(db.committed_meteo, snapshot_meteo)

    def test_schema_guard_aborts_on_missing_column(self) -> None:
        db = FakeOracleDB()
        db.schema_columns["METEOROLOGIA"].remove("VIENTO_180M")
        with TemporaryDirectory() as tmp_wallet:
            cfg = self._make_config(tmp_wallet)
            res = persist_to_oracle(
                SOURCE_OPEN_METEO, METEO_FIXTURE, config=cfg, connector_fn=db.connect
            )
            self.assertFalse(res.executed)
            self.assertEqual(len(db.committed_meteo), 0)
            self.assertEqual(len(db.committed_tiempo), 0)

    def test_cli_dry_run_never_connects(self) -> None:
        with patch("oracle_store.connection.connect_oracle") as mocked_connect:
            for fixture, expected_rows in (
                (REE_FIXTURE, "48 filas"),
                (OMIE_FIXTURE, "24 filas"),
                (METEO_FIXTURE, "168 filas"),
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    exit_code = cli.main(["--file", str(fixture), "--dry-run"])
                self.assertEqual(exit_code, 0)
                out = buf.getvalue()
                self.assertIn(expected_rows, out)
                self.assertIn("No se abrió conexión a Oracle.", out)
            mocked_connect.assert_not_called()

    def test_ingestion_service_unchanged_without_oracle_or_on_error(self) -> None:
        meteo_sample = _load_fixture(METEO_FIXTURE)
        mock_response = {
            "success": True,
            "status_code": 200,
            "source_id": "open_meteo",
            "file_extension": "json",
            "raw_content": json.dumps(meteo_sample),
            "data": meteo_sample,
            "summary": "Descarga exitosa mock",
            "error": None,
        }

        with TemporaryDirectory() as tmp_dir:
            raw_dir = Path(tmp_dir) / "raw"
            with patch("src.services.ingestion_service.STATE_FILE", Path(tmp_dir) / "sources_state.json"):
                service = IngestionService(raw_dir=raw_dir)
                # Caso 1: ORACLE_ENABLED=false
                with patch.dict(os.environ, {"ORACLE_ENABLED": "false"}, clear=False):
                    with patch("src.services.ingestion_service.OpenMeteoClient.fetch_madrid_weather", return_value=mock_response):
                        with self.assertLogs("EcoGrid.Oracle", level="WARNING") as logs:
                            res1 = service.execute_source("open_meteo")
                self.assertTrue(res1["success"])
                self.assertTrue((raw_dir / res1["saved_file"]).is_file())
                self.assertEqual(len(logs.output), 1)

                # Caso 2: ORACLE_ENABLED=true pero sin variables de conexión -> 1 aviso sin error
                clean_env = {
                    k: v
                    for k, v in os.environ.items()
                    if not k.startswith("ORACLE_")
                }
                with patch.dict(os.environ, clean_env, clear=True):
                    with patch("src.services.ingestion_service.OpenMeteoClient.fetch_madrid_weather", return_value=mock_response):
                        with self.assertLogs("EcoGrid.Oracle", level="WARNING") as logs_missing:
                            res_missing = service.execute_source("open_meteo")
                self.assertTrue(res_missing["success"])
                self.assertTrue((raw_dir / res_missing["saved_file"]).is_file())
                self.assertEqual(len(logs_missing.output), 1)

                # Caso 3: persist_to_oracle lanza excepción inesperada -> nunca propaga
                with patch("src.services.ingestion_service.OpenMeteoClient.fetch_madrid_weather", return_value=mock_response):
                    with patch("src.services.ingestion_service.persist_to_oracle", side_effect=RuntimeError("fallo simulado")):
                        res2 = service.execute_source("open_meteo")
                self.assertTrue(res2["success"])
                self.assertTrue((raw_dir / res2["saved_file"]).is_file())

    def test_connect_oracle_thin_mode_retry_and_no_secret_logs(self) -> None:
        with TemporaryDirectory() as tmp_wallet:
            cfg = self._make_config(tmp_wallet)
            fake_conn = FakeConnection(FakeOracleDB())

            with patch.object(
                oracledb,
                "connect",
                side_effect=[TimeoutError("timeout transitorio"), fake_conn],
            ) as mocked_connect:
                with self.assertLogs("EcoGrid.Oracle", level="INFO") as logs:
                    conn = connect_oracle(cfg, max_attempts=2, retry_delay_seconds=0.0)

            self.assertTrue(oracledb.defaults.thin_mode)
            self.assertFalse(conn.autocommit)
            self.assertEqual(mocked_connect.call_count, 2)
            kwargs = mocked_connect.call_args.kwargs
            self.assertEqual(kwargs["tcp_connect_timeout"], 20)
            self.assertEqual(kwargs["config_dir"], tmp_wallet)
            self.assertEqual(kwargs["wallet_location"], tmp_wallet)
            joined_logs = "\n".join(logs.output)
            self.assertIn("ECOGRID", joined_logs)
            self.assertIn("ecogrid_low", joined_logs)
            self.assertNotIn("secret-in-test-only", joined_logs)
            self.assertNotIn("wallet-secret-in-test-only", joined_logs)

            with patch.object(oracledb, "connect", side_effect=TimeoutError("caido")):
                with self.assertRaises(OracleConnectionError):
                    connect_oracle(cfg, max_attempts=2, retry_delay_seconds=0.0)

    def test_ddl_fixture_contains_all_required_tables_and_columns(self) -> None:
        ddl_text = DDL_FIXTURE.read_text(encoding="utf-8").upper()
        for table_name, cols in REQUIRED_SCHEMA_COLUMNS.items():
            self.assertIn(f"CREATE TABLE {table_name}", ddl_text)
            for col in cols:
                self.assertIn(col, ddl_text, f"Columna {col} no hallada en DDL para {table_name}")


if __name__ == "__main__":
    unittest.main()
