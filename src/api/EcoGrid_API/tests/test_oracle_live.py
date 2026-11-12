"""
Test de integración con la base de datos Oracle Autonomous Database en vivo.
Se ejecuta si las credenciales y el wallet están configurados en .env y la BBDD está accesible;
de lo contrario se omite limpiamente (skipTest).
"""

from pathlib import Path
import os
import sys
import unittest

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store.config import OracleConfig
from oracle_store.connection import connect_oracle, verify_schema
from oracle_store.service import dry_run_file, persist_to_oracle

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REE_FIXTURE = FIXTURES_DIR / "ree_esios_20261028_162855.json"
OMIE_FIXTURE = FIXTURES_DIR / "omie_20261028_162854.json"
METEO_FIXTURE = FIXTURES_DIR / "open_meteo_20261028_162853.json"


class TestOracleLiveIntegration(unittest.TestCase):
    """Pruebas de conexión real, guarda de esquema e idempotencia contra Oracle."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = OracleConfig.from_env()
        issue = cls.config.readiness_issue()
        if issue is not None:
            raise unittest.SkipTest(f"Persistencia Oracle no configurada: {issue}")

        try:
            conn = connect_oracle(cls.config, max_attempts=1)
            conn.close()
        except Exception as exc:
            raise unittest.SkipTest(f"Instancia Oracle no alcanzable: {exc}")

    def test_live_schema_verification(self) -> None:
        """Verifica que el esquema físico de Oracle coincide con crearTablasBBDDEcoGrid_v3.sql."""
        conn = connect_oracle(self.config)
        try:
            verify_schema(conn, self.config)
        finally:
            conn.close()

    def test_live_persistence_and_idempotency_all_sources(self) -> None:
        """Verifica persistencia y reejecución idempotente en vivo para las 3 fuentes."""
        # 1. REE
        res_ree1 = persist_to_oracle("ree_esios", REE_FIXTURE, config=self.config)
        self.assertTrue(res_ree1.executed)
        self.assertEqual(res_ree1.rows_merged, 48)

        res_ree2 = persist_to_oracle("ree_esios", REE_FIXTURE, config=self.config)
        self.assertTrue(res_ree2.executed)
        self.assertEqual(res_ree2.rows_merged, 48)

        # 2. OMIE
        res_omie1 = persist_to_oracle("omie", OMIE_FIXTURE, config=self.config)
        self.assertTrue(res_omie1.executed)
        self.assertEqual(res_omie1.rows_merged, 24)

        res_omie2 = persist_to_oracle("omie", OMIE_FIXTURE, config=self.config)
        self.assertTrue(res_omie2.executed)
        self.assertEqual(res_omie2.rows_merged, 24)

        # 3. Open-Meteo
        res_meteo1 = persist_to_oracle("open_meteo", METEO_FIXTURE, config=self.config)
        self.assertTrue(res_meteo1.executed)
        self.assertEqual(res_meteo1.rows_merged, 168)

        res_meteo2 = persist_to_oracle("open_meteo", METEO_FIXTURE, config=self.config)
        self.assertTrue(res_meteo2.executed)
        self.assertEqual(res_meteo2.rows_merged, 168)


if __name__ == "__main__":
    unittest.main()

