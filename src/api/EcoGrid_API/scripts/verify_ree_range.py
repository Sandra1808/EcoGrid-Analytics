"""
Script ejecutable para verificar la continuidad horaria de REE en Oracle.
Uso:
    python scripts/verify_ree_range.py
"""

from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from oracle_store.verify import main

if __name__ == "__main__":
    raise SystemExit(main())

