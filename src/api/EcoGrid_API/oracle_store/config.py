"""
Configuración del módulo de persistencia Oracle para EcoGrid Analytics.
Carga variables de entorno desde .env (sin sobrescribir el entorno del proceso)
y valida disponibilidad de credenciales sin exponer secretos.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os

from dotenv import load_dotenv

_ENV_LOADED = False


def load_project_env() -> None:
    """Carga EcoGrid_API/.env una sola vez sin sobrescribir variables existentes."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    _ENV_LOADED = True


def _parse_bool(raw: Optional[str], default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "si", "sí", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(raw: Optional[str], default: int, minimum: int = 1) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        parsed = int(raw.strip())
        return parsed if parsed >= minimum else default
    except ValueError:
        return default


def _parse_float(raw: Optional[str], default: float) -> float:
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


@dataclass
class OracleConfig:
    """Parámetros de conexión, calendario y validación para persistencia en Oracle."""

    enabled: bool = True
    user: str = ""
    password: str = field(default="", repr=False)
    dsn: str = ""
    wallet_dir: str = ""
    wallet_password: str = field(default="", repr=False)
    connect_timeout: int = 20
    calendar_tz_name: str = "Europe/Madrid"
    nacional_ccaa_codine: str = "00"
    meteo_ccaa_codine: str = "13"
    ree_min_mw: float = 15000.0
    ree_max_mw: float = 45000.0
    omie_min_price: float = -500.0
    omie_max_price: float = 4000.0
    meteo_ref_lat: float = 40.4176
    meteo_ref_lon: float = -3.7394
    meteo_coord_tolerance: float = 0.5

    @classmethod
    def from_env(cls) -> "OracleConfig":
        """Construye la configuración leyendo variables de entorno."""
        load_project_env()
        return cls(
            enabled=_parse_bool(os.getenv("ORACLE_ENABLED"), default=True),
            user=(os.getenv("ORACLE_USER") or "").strip(),
            password=os.getenv("ORACLE_PASSWORD") or "",
            dsn=(os.getenv("ORACLE_DSN") or "").strip(),
            wallet_dir=(os.getenv("ORACLE_WALLET_DIR") or "").strip(),
            wallet_password=os.getenv("ORACLE_WALLET_PASSWORD") or "",
            connect_timeout=_parse_int(os.getenv("ORACLE_CONNECT_TIMEOUT"), default=20, minimum=1),
            calendar_tz_name=(os.getenv("CALENDAR_TZ") or "Europe/Madrid").strip(),
            nacional_ccaa_codine=(os.getenv("NACIONAL_CCAA_CODINE") or "00").strip(),
            meteo_ccaa_codine=(os.getenv("METEO_CCAA_CODINE") or "13").strip(),
            ree_min_mw=_parse_float(os.getenv("REE_DEMAND_MIN_MW"), default=15000.0),
            ree_max_mw=_parse_float(os.getenv("REE_DEMAND_MAX_MW"), default=45000.0),
            omie_min_price=_parse_float(os.getenv("OMIE_PRICE_MIN_EUR"), default=-500.0),
            omie_max_price=_parse_float(os.getenv("OMIE_PRICE_MAX_EUR"), default=4000.0),
        )

    @property
    def calendar_tz(self) -> ZoneInfo:
        """Devuelve ZoneInfo válido para CALENDAR_TZ."""
        try:
            return ZoneInfo(self.calendar_tz_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Zona horaria CALENDAR_TZ inválida: {self.calendar_tz_name}") from exc

    def has_auto_login_wallet(self) -> bool:
        """Indica si existe cwallet.sso en ORACLE_WALLET_DIR."""
        if not self.wallet_dir:
            return False
        return (Path(self.wallet_dir) / "cwallet.sso").is_file()

    def missing_connection_vars(self) -> List[str]:
        """Lista las variables de conexión obligatorias que faltan."""
        missing: List[str] = []
        if not self.user:
            missing.append("ORACLE_USER")
        if not self.password:
            missing.append("ORACLE_PASSWORD")
        if not self.dsn:
            missing.append("ORACLE_DSN")
        if not self.wallet_dir:
            missing.append("ORACLE_WALLET_DIR")
        if not self.wallet_password and not self.has_auto_login_wallet():
            missing.append("ORACLE_WALLET_PASSWORD")
        return missing

    def readiness_issue(self) -> Optional[str]:
        """
        Devuelve el motivo si Oracle está deshabilitado o sin configurar,
        o None si la configuración es suficiente para intentar conectar.
        """
        if not self.enabled:
            return "ORACLE_ENABLED=false"
        missing = self.missing_connection_vars()
        if missing:
            return f"faltan variables de conexión ({', '.join(missing)})"
        if not Path(self.wallet_dir).is_dir():
            return "el directorio configurado en ORACLE_WALLET_DIR no existe"
        return None

