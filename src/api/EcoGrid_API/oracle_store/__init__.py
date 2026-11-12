"""
Paquete de persistencia en Oracle 21c / Autonomous Database para EcoGrid Analytics.
"""

from oracle_store.config import OracleConfig
from oracle_store.service import DryRunReport, PersistResult, dry_run_file, persist_to_oracle

__all__ = [
    "DryRunReport",
    "OracleConfig",
    "PersistResult",
    "dry_run_file",
    "persist_to_oracle",
]

