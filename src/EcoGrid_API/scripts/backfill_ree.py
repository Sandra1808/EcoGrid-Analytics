"""
Script ejecutable para lanzar el backfill histórico de REE.
Uso:
    python scripts/backfill_ree.py --start-date 2026-10-29
"""

from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store.backfill import main

if __name__ == "__main__":
    raise SystemExit(main())

