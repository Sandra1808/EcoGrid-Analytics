# Persistencia en Oracle 21c / Autonomous Database (`oracle_store`)

Documentación técnica de la integración no bloqueante para persistir en Oracle los JSON descargados por **EcoGrid Analytics** (`REE`, `OMIE` y `Open-Meteo`), el módulo de backfill histórico, el modo de visibilidad de errores y la configuración del programador de tareas.

---

## 1. Resumen de lo hecho y componentes del sistema

### Módulos y scripts creados
- `src/EcoGrid_API/oracle_store/__init__.py` — Exporta `persist_to_oracle`, `dry_run_file`, `OracleConfig`, `PersistResult` y `DryRunReport`.
- `src/EcoGrid_API/oracle_store/config.py` — Carga segura de variables desde `.env` (`override=False`), `OracleConfig` con contraseñas ocultas en `repr()` y validación de disponibilidad (`readiness_issue()`).
- `src/EcoGrid_API/oracle_store/connection.py` — Conexión `python-oracledb` en modo *Thin* con wallet mTLS, reintentos de conexión (máx. 2) y guarda de esquema de solo lectura sobre `USER_TAB_COLUMNS` y `ComunidadAutonoma`.
- `src/EcoGrid_API/oracle_store/time_dimension.py` — Gestión de `TiempoHorario` (`idTiempo = YYYYMMDDHH` UTC, calendario `Europe/Madrid`), FestivosBOE, y clase `TiempoMap` que rastrea exactamente horas insertadas vs existentes.
- `src/EcoGrid_API/oracle_store/transformers.py` — Transformadores puros sin acceso a BBDD para REE, OMIE y Open-Meteo, con agregación horaria UTC, validación de rangos y desambiguación DST (`fold=0`/`fold=1`).
- `src/EcoGrid_API/oracle_store/repository.py` — Consultas con variables bind (`:param`), sentencias `MERGE INTO` idempotentes por lotes con `COALESCE(nuevo, actual)`, `setinputsizes` y detección exacta de filas insertadas vs actualizadas (`MergeStats`).
- `src/EcoGrid_API/oracle_store/service.py` — Orquestación transaccional con modo dual: no bloqueante para la API (`raise_on_error=False`) y explícito para backfill/CLI (`raise_on_error=True`), con desglose de filas insertadas/actualizadas.
- `src/EcoGrid_API/oracle_store/cli.py` — CLI con soporte para `--dry-run`, `--raise-on-error`, autodetección de fuente y reporte exhaustivo de conexión y conteos.
- `src/EcoGrid_API/oracle_store/backfill.py` — Motor de backfill histórico parametrizable por fechas, descarga y almacenamiento en `data/raw/` y persistencia en Oracle con reporte diario.
- `src/EcoGrid_API/oracle_store/verify.py` — Verificador de continuidad horaria que detecta gaps y calcula estadísticas de demanda real y previsiones.
- `src/EcoGrid_API/scripts/backfill_ree.py` y `scripts/verify_ree_range.py` — Scripts de acceso directo para backfill y verificación.
- `src/EcoGrid_API/tests/test_oracle_store.py` — 15 pruebas unitarias en memoria.
- `src/EcoGrid_API/tests/test_oracle_live.py` — 2 pruebas de integración en vivo contra Oracle Autonomous Database.

---

## 2. Parámetros de Conexión y Variables de Entorno

- **Driver:** `python-oracledb` (`oracledb>=2.0.0`) configurado en **modo Thin** (`oracledb.defaults.thin_mode = True`).
- **Wallet mTLS:** Descomprimido en `C:\Oracle\EcoGrid\wallet` fuera del repositorio y protegido en `.gitignore`.
- **Configuración en `src/EcoGrid_API/.env`:**

| Variable | Valor configurado | Descripción |
| :--- | :--- | :--- |
| `ORACLE_ENABLED` | `true` | Activa la capa de persistencia en Oracle. |
| `ORACLE_USER` | `ECOGRID` | Usuario del esquema de la base de datos. |
| `ORACLE_PASSWORD` | `Pr0yect0BigData_Ec0grid@` | Contraseña del usuario Oracle. |
| `ORACLE_DSN` | `ecogriddb_low` | Alias de servicio en `tnsnames.ora`. |
| `ORACLE_WALLET_DIR` | `C:\Oracle\EcoGrid\wallet` | Carpeta local del wallet mTLS descomprimido. |
| `ORACLE_WALLET_PASSWORD` | `Ec0gridwallet@` | Contraseña del wallet. |
| `ORACLE_CONNECT_TIMEOUT` | `20` | Timeout TCP en segundos. |
| `CALENDAR_TZ` | `Europe/Madrid` | Zona horaria para derivar campos de calendario. |
| `NACIONAL_CCAA_CODINE` | `00` | Código INE para España nacional (REE). |
| `METEO_CCAA_CODINE` | `13` | Código INE para Comunidad de Madrid. |

---

## 3. Manejo Transparente de Errores y Visibilidad

Para conciliar la tolerancia a fallos en el gestor de APIs con la visibilidad estricta requerida en tareas operativas (como backfill o ejecuciones manuales), el sistema ofrece **modo dual**:

1. **Modo Silencioso / No Bloqueante (`raise_on_error=False`, por defecto):**
   - Utilizado por `IngestionService.execute_source` y las tareas planificadas.
   - Si la BBDD está apagada, falla la red o faltan credenciales, registra una línea de aviso en log y retorna `PersistResult(executed=False, skipped=True, reason=...)` sin propagar excepciones ni romper la respuesta HTTP.
2. **Modo Explícito / Transparente (`raise_on_error=True` o flag `--raise-on-error` en CLI):**
   - Utilizado por el motor de backfill (`oracle_store.backfill`) y ejecuciones CLI manuales de diagnóstico.
   - Cualquier error de conexión (`OracleConnectionError`), validación de esquema (`SchemaValidationError`) o transacción SQL (`ORA-XXXXX`) se propaga de inmediato con traceback completo, informando del estado exacto del conector.
   - Proporciona un desglose exhaustivo de conteos:
     ```
     [OK] ree_esios -> DemandaGeneracionREE:
       Estado de conexión: Conectado a Oracle (usuario=ECOGRID, dsn=ecogriddb_low)
       Filas en DemandaGeneracionREE: 24 (24 insertadas, 0 actualizadas)
       Horas en TiempoHorario: 24 (0 insertadas, 24 existentes)
     ```

---

## 4. Backfill Histórico de REE (29/10/2026 hasta hoy)

Se ejecutó el backfill histórico para la demanda eléctrica peninsular española (`idCCAA=1` / `codIne='00'`):
- **Comando:**
  ```powershell
  cd src/EcoGrid_API
  python -m oracle_store.backfill --start-date 2026-10-29
  ```
- **Rango cubierto:** Desde el 29/10/2026 00:00 local (`2026-10-28 23:00:00 UTC`) hasta el 12/11/2026 (`2026-11-12 01:00:00 UTC`).
- **Archivos generados en disco (`data/raw/`):**
  - Se descargaron y almacenaron 15 archivos JSON brutos (`ree_esios_backfill_20261029.json` hasta `ree_esios_backfill_20261112.json`), preservando el formato original para el modelo de IA.
- **Resultado en Oracle:**
  - **Días procesados:** 15 días.
  - **Filas en `DemandaGeneracionREE`:** 339 filas procesadas (339 nuevas insertadas en primera ejecución).
  - **Horas en `TiempoHorario`:** 339 horas aseguradas (192 insertadas y 147 reutilizadas de previsiones).
  - **Prueba de Idempotencia:** Reejecución completa consecutiva: 339 filas actualizadas por `MERGE`, 0 duplicadas, 0 errores.

---

## 5. Verificación de Continuidad y Completitud (0 Gaps)

Se ejecutó el script de verificación `oracle_store.verify`:
- **Comando:**
  ```powershell
  cd src/EcoGrid_API
  python -m oracle_store.verify --since 2026-10-28T23:00:00
  ```
- **Métricas obtenidas:**
  - **Rango evaluado (UTC):** `2026-10-28T23:00:00Z` -> `2026-11-12T01:00:00Z`
  - **Horas esperadas en el rango:** 339 horas consecutivas.
  - **Horas registradas en BBDD:** 339 horas.
  - **Horas faltantes (gaps):** **0 horas (100% continuidad garantizada)**.
  - **Horas con demanda real completa (12/12 puntos):** 330 horas.
  - **Horas parciales (Real=NULL, previstas con valor):** 9 horas (correspondientes a horas en curso o incompletas en origen).
  - **Horas con demanda prevista:** 339 horas.
  - **Horas con demanda programada:** 339 horas.
  - **Estadísticas de demanda real peninsular:**
    - Mínimo: 19.809,67 MW
    - Media: 29.035,80 MW
    - Máximo: 36.543,67 MW

---

## 6. Estado Global de Tablas en Oracle Autonomous DB

| Tabla | Total Filas | Rango Temporal UTC |
| :--- | :---: | :--- |
| `TiempoHorario` | 1.417 | 2026-09-20 22:00:00 → 2026-11-18 22:00:00 |
| `DemandaGeneracionREE` | 1.252 | 2026-09-20 22:00:00 → 2026-11-12 01:00:00 |
| `PreciosMercadoOmie` | 913 | 2026-09-20 22:00:00 → 2026-10-28 22:00:00 |
| `Meteorologia` | 1.225 | 2026-09-20 22:00:00 → 2026-11-18 22:00:00 |

---

## 7. Configuración de Ingesta Periódica (Programador Inactivo)

En `src/EcoGrid_API/config/tasks.yaml`, la tarea periódica para la demanda de REE queda completamente parametrizada y **explícitamente desactivada**:

```yaml
  ree_demanda_tiempo_real:
    name: REE / ESIOS Demanda Eléctrica Peninsular
    connector: ree_esios
    enabled: false               # <-- Inactiva hasta confirmación del equipo
    interval_minutes: 30
    cron: '*/30 * * * *'
    destination_dir: data/raw
    description: Monitorización de demanda real peninsular e indicativa con soporte de token ESIOS y fallback público
    params:
      indicator_real: 1293
      indicator_forecast: 460
```

- Al iniciar el servidor o planificador (`SchedulerService`), APScheduler evalúa `task_cfg.get("enabled", False)`. Al ser `false`, la tarea **no se registra ni se dispara automáticamente**.
- Para activarla en el futuro (una vez validado el backfill), basta con cambiar `enabled: true` en `tasks.yaml` o mediante la interfaz de administración del dashboard.
