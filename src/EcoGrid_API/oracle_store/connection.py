"""
Gestión de conexión Oracle en modo Thin (mTLS con wallet) y guarda de esquema de solo lectura.
Nunca registra contraseñas ni contenido del wallet en logs.
"""

from typing import Any, Dict, Iterable, Optional, Set, Tuple
import logging
import time

from oracle_store.config import OracleConfig

logger = logging.getLogger("EcoGrid.Oracle")

try:
    import oracledb
except ImportError:  # pragma: no cover - manejado explícitamente si falta el paquete
    oracledb = None  # type: ignore[assignment]


REQUIRED_SCHEMA_COLUMNS: Dict[str, Set[str]] = {
    "TIEMPOHORARIO": {
        "IDTIEMPO",
        "FECHORA",
        "FECHA",
        "HORA",
        "DIASEMANA",
        "MES",
        "YEAR",
        "INDFINSEMANA",
        "INDFESTIVO",
    },
    "COMUNIDADAUTONOMA": {
        "IDCCAA",
        "CODINE",
    },
    "FESTIVOSBOE": {
        "FECHA",
        "AMBITO",
    },
    "PRECIOSMERCADOOMIE": {
        "IDTIEMPO",
        "PRECIOMARGINALES",
        "PRECIOMARGINALPT",
        "TIPMERCADO",
    },
    "METEOROLOGIA": {
        "IDTIEMPO",
        "IDCCAA",
        "TEMPERATURA_2M",
        "VIENTO_10M",
        "VIENTO_80M",
        "VIENTO_120M",
        "VIENTO_180M",
        "VIENTO_DIR_10M",
        "VIENTO_DIR_80M",
        "VIENTO_DIR_120M",
        "VIENTO_DIR_180M",
        "RADIACION_DIRECTA",
        "SHORTWAVE_RADIATION",
        "GLOBAL_TILTED_IRRADIANCE",
        "COBERTURA_NUBES",
        "HUMEDAD_RELATIVA",
    },
    "DEMANDAGENERACIONREE": {
        "IDTIEMPO",
        "IDCCAA",
        "DEMANDAREALMW",
        "DEMANDAPREVISTAREEMW",
        "DEMANDAPROGRAMADAMW",
        "DEMANDAPROGRAMADATOTALMW",
    },
}

_SCHEMA_COLUMNS_SQL = """
SELECT table_name, column_name
FROM USER_TAB_COLUMNS
WHERE table_name IN (
    'TIEMPOHORARIO',
    'COMUNIDADAUTONOMA',
    'FESTIVOSBOE',
    'PRECIOSMERCADOOMIE',
    'METEOROLOGIA',
    'DEMANDAGENERACIONREE'
)
"""

_CCAA_CHECK_SQL = """
SELECT codIne
FROM ComunidadAutonoma
WHERE codIne IN (:cod_nacional, :cod_meteo)
"""

_VERIFIED_SCHEMAS: Set[Tuple[str, str, str, str]] = set()


class SchemaValidationError(RuntimeError):
    """Error lanzado cuando el esquema Oracle no cumple los requisitos esperados."""


class OracleConnectionError(RuntimeError):
    """Error lanzado cuando falla la conexión con Oracle tras los reintentos."""


def reset_schema_cache() -> None:
    """Limpia la caché de verificación de esquema (útil en tests)."""
    _VERIFIED_SCHEMAS.clear()


def extract_oracle_error_code(exc: BaseException) -> Optional[int]:
    """Extrae el código numérico ORA-XXXXX desde una excepción de oracledb."""
    args = getattr(exc, "args", ())
    for arg in args:
        code = getattr(arg, "code", None)
        if isinstance(code, int):
            return code
    text = str(exc)
    for prefix in ("ORA-",):
        idx = text.find(prefix)
        if idx != -1:
            digits = ""
            for ch in text[idx + len(prefix) : idx + len(prefix) + 6]:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                return int(digits)
    return None


def _is_transient_connection_error(exc: BaseException) -> bool:
    code = extract_oracle_error_code(exc)
    if code in {1017, 28000, 1005}:  # Credenciales inválidas o cuenta bloqueada: no reintentar
        return False
    if isinstance(exc, (TimeoutError, OSError)):
        return True
    if oracledb is not None and isinstance(exc, getattr(oracledb, "OperationalError", ())):
        return True
    text = str(exc)
    return any(
        marker in text
        for marker in ("DPY-6", "DPY-4011", "ORA-12170", "ORA-12541", "ORA-12514", "timed out")
    )


def set_cursor_inputsizes(cursor: Any, **sizes: str) -> None:
    """Configura tipos bind en executemany evitando errores con valores NULL."""
    if oracledb is None or not hasattr(cursor, "setinputsizes"):
        return
    type_map = {
        "NUMBER": oracledb.DB_TYPE_NUMBER,
        "VARCHAR": oracledb.DB_TYPE_VARCHAR,
        "TIMESTAMP": oracledb.DB_TYPE_TIMESTAMP,
        "DATE": oracledb.DB_TYPE_DATE,
    }
    resolved = {k: type_map[v] for k, v in sizes.items() if v in type_map}
    if resolved:
        cursor.setinputsizes(**resolved)


def connect_oracle(
    config: OracleConfig,
    max_attempts: int = 2,
    retry_delay_seconds: float = 0.5,
) -> Any:
    """
    Abre conexión Oracle en modo Thin con wallet mTLS (máx. 2 intentos en errores de conexión).
    Solo loguea usuario y alias del servicio (nunca contraseñas ni rutas de wallet sensibles).
    """
    if oracledb is None:
        raise OracleConnectionError("La librería 'oracledb' no está instalada en el entorno.")

    oracledb.defaults.thin_mode = True
    last_exc: Optional[BaseException] = None

    for attempt in range(1, max_attempts + 1):
        try:
            connection = oracledb.connect(
                user=config.user,
                password=config.password,
                dsn=config.dsn,
                config_dir=config.wallet_dir,
                wallet_location=config.wallet_dir,
                wallet_password=config.wallet_password or None,
                tcp_connect_timeout=config.connect_timeout,
            )
            connection.autocommit = False
            logger.info(
                "Conexión Oracle establecida (modo Thin, usuario=%s, dsn=%s).",
                config.user,
                config.dsn,
            )
            return connection
        except Exception as exc:
            last_exc = exc
            can_retry = attempt < max_attempts and _is_transient_connection_error(exc)
            logger.warning(
                "Fallo de conexión Oracle (intento %s/%s, usuario=%s, dsn=%s): %s",
                attempt,
                max_attempts,
                config.user,
                config.dsn,
                exc,
            )
            if can_retry:
                time.sleep(retry_delay_seconds)
                continue
            break

    raise OracleConnectionError(
        f"No se pudo conectar a Oracle (usuario={config.user}, dsn={config.dsn}): {last_exc}"
    )


def verify_schema(connection: Any, config: OracleConfig) -> None:
    """
    Guarda de esquema de solo lectura: en la primera conexión de cada ejecución
    verifica en USER_TAB_COLUMNS las tablas/columnas requeridas y los codIne en ComunidadAutonoma.
    """
    cache_key = (
        config.user.upper(),
        config.dsn,
        config.nacional_ccaa_codine,
        config.meteo_ccaa_codine,
    )
    if cache_key in _VERIFIED_SCHEMAS:
        return

    found_columns: Dict[str, Set[str]] = {}
    with connection.cursor() as cursor:
        cursor.execute(_SCHEMA_COLUMNS_SQL)
        for table_name, column_name in cursor.fetchall():
            t_up = str(table_name).strip().upper()
            c_up = str(column_name).strip().upper()
            found_columns.setdefault(t_up, set()).add(c_up)

        missing_tables: list[str] = []
        missing_cols: list[str] = []
        for table_name, req_cols in REQUIRED_SCHEMA_COLUMNS.items():
            present = found_columns.get(table_name)
            if not present:
                missing_tables.append(table_name)
                continue
            diff = sorted(req_cols - present)
            if diff:
                missing_cols.append(f"{table_name}({', '.join(diff)})")

        if missing_tables or missing_cols:
            details: list[str] = []
            if missing_tables:
                details.append(f"tablas ausentes: {', '.join(missing_tables)}")
            if missing_cols:
                details.append(f"columnas ausentes: {', '.join(missing_cols)}")
            raise SchemaValidationError(
                "Guarda de esquema Oracle fallida en USER_TAB_COLUMNS: " + "; ".join(details)
            )

        cursor.execute(
            _CCAA_CHECK_SQL,
            {
                "cod_nacional": config.nacional_ccaa_codine,
                "cod_meteo": config.meteo_ccaa_codine,
            },
        )
        found_codines = {str(row[0]).strip() for row in cursor.fetchall()}

    required_codines = {config.nacional_ccaa_codine, config.meteo_ccaa_codine}
    missing_codines = sorted(required_codines - found_codines)
    if missing_codines:
        raise SchemaValidationError(
            f"ComunidadAutonoma no contiene los codIne requeridos: {', '.join(missing_codines)}"
        )

    _VERIFIED_SCHEMAS.add(cache_key)
    logger.info(
        "Guarda de esquema Oracle verificada correctamente (usuario=%s, dsn=%s).",
        config.user,
        config.dsn,
    )
