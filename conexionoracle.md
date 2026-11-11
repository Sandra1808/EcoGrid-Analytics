# Persistencia en Oracle 21c / Autonomous Database (`oracle_store`)

Documentación técnica de la integración no bloqueante para persistir en Oracle los JSON descargados por **EcoGrid Analytics** (`REE`, `OMIE` y `Open-Meteo`), manteniendo intacto el comportamiento previo del gestor de APIs y del almacenamiento local en `EcoGrid_API/data/raw/`.

---

## 1. Resumen de lo hecho y diff exacto del cambio mínimo

### Archivos nuevos creados
- `EcoGrid_API/oracle_store/__init__.py` — Exporta `persist_to_oracle`, `dry_run_file`, `OracleConfig`, `PersistResult` y `DryRunReport`.
- `EcoGrid_API/oracle_store/config.py` — Carga segura de variables desde `EcoGrid_API/.env` (`override=False`), `OracleConfig` con contraseñas ocultas en `repr()` y validación de disponibilidad (`readiness_issue()`).
- `EcoGrid_API/oracle_store/connection.py` — Conexión `python-oracledb` en modo *Thin* con wallet mTLS, reintentos de conexión (máx. 2 intentos) y guarda de esquema de solo lectura sobre `USER_TAB_COLUMNS` y `ComunidadAutonoma`.
- `EcoGrid_API/oracle_store/time_dimension.py` — Cálculo de `TiempoHorario` (`idTiempo = YYYYMMDDHH` UTC, calendario local en `CALENDAR_TZ`) y consulta en bloque de `FestivosBOE`.
- `EcoGrid_API/oracle_store/transformers.py` — Transformadores puros sin acceso a BBDD para `ree_esios`, `omie` y `open_meteo`, con autodetección de fuente, agregación horaria UTC, validación de rangos y desambiguación DST (`fold=0`/`fold=1`).
- `EcoGrid_API/oracle_store/repository.py` — Consultas de lectura (`ComunidadAutonoma`) y `MERGE` idempotentes por lotes con `COALESCE(nuevo, actual)` y `setinputsizes(...)`.
- `EcoGrid_API/oracle_store/service.py` — Orquestación transaccional por fuente (`TiempoHorario` + `MERGE` + `COMMIT`), reintentos en `ORA-00001` / `ORA-00060`, `ROLLBACK` en fallo y aislamiento total frente a errores (`persist_to_oracle` nunca propaga excepciones).
- `EcoGrid_API/oracle_store/cli.py` — CLI con autodetección de fuente y modo `--dry-run`.
- `EcoGrid_API/tests/fixtures/` — Copias de referencia: `crearTablasBBDDEcoGrid_v3.sql`, `ree_esios_20261028_162855.json`, `omie_20261028_162854.json`, `open_meteo_20261028_162853.json`.
- `EcoGrid_API/tests/test_oracle_store.py` — Suite de 15 tests unitarios y de integración simulada sin requerir instancia Oracle.
- `conexionoracle.md` — Este documento.

### Diff exacto de los archivos existentes modificados

```diff
diff --git a/.gitignore b/.gitignore
index 83972fa..e3def71 100644
--- a/.gitignore
+++ b/.gitignore
@@ -150,6 +150,14 @@ activemq-data/
 # Environments
 .env
 .envrc
+wallet/
+*wallet*/
+*.sso
+ewallet.p12
+ewallet.pem
+tnsnames.ora
+sqlnet.ora
+ojdbc.properties
 .venv
 env/
 venv/
diff --git a/EcoGrid_API/.env.example b/EcoGrid_API/.env.example
index aa9dd6c..47fa52e 100644
--- a/EcoGrid_API/.env.example
+++ b/EcoGrid_API/.env.example
@@ -5,3 +5,16 @@ DATA_DIR=data/raw
 
 # Claves de APIs Externas
 ESIOS_API_TOKEN=tu_token_aqui
+
+# Persistencia Oracle 21c / Autonomous Database (modo Thin + Wallet mTLS)
+# El wallet debe residir descomprimido fuera del repositorio.
+ORACLE_ENABLED=true
+ORACLE_USER=ECOGRID
+ORACLE_PASSWORD=
+ORACLE_DSN=
+ORACLE_WALLET_DIR=
+ORACLE_WALLET_PASSWORD=
+ORACLE_CONNECT_TIMEOUT=20
+CALENDAR_TZ=Europe/Madrid
+NACIONAL_CCAA_CODINE=00
+METEO_CCAA_CODINE=13
diff --git a/EcoGrid_API/.gitignore b/EcoGrid_API/.gitignore
index 0084089..88a2a9f 100644
--- a/EcoGrid_API/.gitignore
+++ b/EcoGrid_API/.gitignore
@@ -12,6 +12,14 @@ __pycache__/
 
 # Configuración local y secretos
 .env
+wallet/
+*wallet*/
+*.sso
+ewallet.p12
+ewallet.pem
+tnsnames.ora
+sqlnet.ora
+ojdbc.properties
 .vscode/
 .idea/
 
diff --git a/EcoGrid_API/requirements.txt b/EcoGrid_API/requirements.txt
index 47b2810..ed42ab2 100644
--- a/EcoGrid_API/requirements.txt
+++ b/EcoGrid_API/requirements.txt
@@ -8,3 +8,4 @@ jinja2>=3.1.2
 httpx>=0.24.0
 apscheduler>=3.10.0
 pyyaml>=6.0.0
+oracledb>=2.0.0
diff --git a/EcoGrid_API/src/services/ingestion_service.py b/EcoGrid_API/src/services/ingestion_service.py
index 9b53457..c8657be 100644
--- a/EcoGrid_API/src/services/ingestion_service.py
+++ b/EcoGrid_API/src/services/ingestion_service.py
@@ -7,13 +7,17 @@ from typing import Dict, Any, List, Optional, Union
 from datetime import datetime
 from pathlib import Path
 import json
+import logging
 import os
 
+from oracle_store import persist_to_oracle
 from src.config.settings import DATA_RAW_DIR, ESIOS_API_TOKEN
 from src.connectors.meteo_client import OpenMeteoClient
 from src.connectors.omie_client import OMIEClient
 from src.connectors.ree_client import REEClient
 
+logger = logging.getLogger("EcoGrid.Ingestion")
+
 STATE_FILE = DATA_RAW_DIR.parent / "sources_state.json"
 
 class IngestionService:
@@ -173,6 +177,12 @@ class IngestionService:
                 result["error"] = f"Error al guardar archivo en disco: {e}"
                 saved_filename = None
 
+        if result.get("success") and saved_filename is not None:
+            try:
+                persist_to_oracle(source_id, file_path)
+            except Exception as oracle_err:
+                logger.warning("Error no bloqueante al persistir %s en Oracle: %s", source_id, oracle_err)
+
         # Registrar estado de la última ejecución
         status_label = "SUCCESS" if result.get("success") else "ERROR"
         last_run_info = {
```

---

## 2. Cómo conecta con Oracle

- **Driver:** `python-oracledb` (`oracledb>=2.0.0`) configurado explícitamente en **modo Thin** (`oracledb.defaults.thin_mode = True`), por lo que no requiere Oracle Instant Client ni librerías nativas.
- **Wallet mTLS (Autonomous Database):** El archivo ZIP del wallet descargado desde OCI debe descomprimirse en una carpeta **fuera del repositorio** (por ejemplo `C:\oracle\wallets\ecogrid_wallet`). La conexión pasa `config_dir` y `wallet_location` apuntando a `ORACLE_WALLET_DIR`, y `wallet_password` con `ORACLE_WALLET_PASSWORD` (si existe `cwallet.sso` de auto-login y no se indica contraseña de wallet, permite `wallet_password=None`).
- **Autocommit y timeout:** `connection.autocommit = False` explícito y `tcp_connect_timeout` configurable mediante `ORACLE_CONNECT_TIMEOUT` (por defecto `20` segundos).
- **Variables de entorno** (en `EcoGrid_API/.env`, documentadas en [EcoGrid_API/.env.example](file:///c:/Users/USER/Desktop/EcoGrid-Analytics/EcoGrid_API/.env.example)):

| Variable | Obligatoria | Valor por defecto | Descripción |
| :--- | :---: | :--- | :--- |
| `ORACLE_ENABLED` | No | `true` | Activa/desactiva la persistencia Oracle (`true`/`false`). |
| `ORACLE_USER` | Sí | — | Usuario de esquema de aplicación (ej. `ECOGRID`, nunca `ADMIN`). |
| `ORACLE_PASSWORD` | Sí | — | Contraseña del usuario Oracle. |
| `ORACLE_DSN` | Sí | — | Alias de servicio definido en `tnsnames.ora` (ej. `ecogrid_tp` / `ecogrid_low`). |
| `ORACLE_WALLET_DIR` | Sí | — | Ruta absoluta a la carpeta del wallet descomprimido fuera del repo. |
| `ORACLE_WALLET_PASSWORD` | Sí* | — | Contraseña del wallet (*opcional solo si existe `cwallet.sso` en `ORACLE_WALLET_DIR`). |
| `ORACLE_CONNECT_TIMEOUT` | No | `20` | Timeout TCP de conexión en segundos. |
| `CALENDAR_TZ` | No | `Europe/Madrid` | Zona horaria local para derivar `fecha`, `hora`, `diaSemana`, `mes`, `year`, `indFinSemana` e `indFestivo`. |
| `NACIONAL_CCAA_CODINE` | No | `00` | Código INE en `ComunidadAutonoma` para datos nacionales (REE). |
| `METEO_CCAA_CODINE` | No | `13` | Código INE en `ComunidadAutonoma` para meteorología (Open-Meteo Madrid). |

---

## 3. Flujo de ejecución y tolerancia a fallos

1. [`IngestionService.execute_source`](file:///c:/Users/USER/Desktop/EcoGrid-Analytics/EcoGrid_API/src/services/ingestion_service.py#L126-L208) (invocado tanto por los endpoints REST manuales como por [`SchedulerService.execute_task_now`](file:///c:/Users/USER/Desktop/EcoGrid-Analytics/EcoGrid_API/src/services/scheduler_service.py#L148-L215)) llama primero al conector HTTP y guarda el JSON en `EcoGrid_API/data/raw/` exactamente igual que antes.
2. **Solo si el JSON ya se guardó correctamente en disco**, ejecuta `persist_to_oracle(source_id, file_path)` dentro de un bloque `try/except Exception`.
3. **Omisión limpia:** Si `ORACLE_ENABLED=false`, falta alguna variable de conexión o `ORACLE_WALLET_DIR` no existe, emite **una única línea de aviso (`WARNING`)** en el log y retorna sin abrir conexiones ni alterar `sources_state.json`, códigos HTTP ni respuesta de la API.
4. **Transformación previa:** El JSON se transforma y valida en memoria antes de abrir conexión Oracle; si no hay filas válidas (por ejemplo, coordenadas fuera de tolerancia o formato no soportado), no abre conexión.
5. **Conexión y guarda de esquema:**
   - Reintento de conexión: hasta **2 intentos** ante errores transitorios de red/timeout (`ORA-12xxx`, `DPY-6xxx`, `TimeoutError`, `OperationalError`), sin reintentar errores de credenciales (`ORA-01017`, `ORA-28000`).
   - En la primera conexión válida del proceso, [`verify_schema`](file:///c:/Users/USER/Desktop/EcoGrid-Analytics/EcoGrid_API/oracle_store/connection.py#L183-L246) consulta `USER_TAB_COLUMNS` (tablas `TIEMPOHORARIO`, `COMUNIDADAUTONOMA`, `FESTIVOSBOE`, `PRECIOSMERCADOOMIE`, `METEOROLOGIA`, `DEMANDAGENERACIONREE`) y verifica los `codIne` configurados en `ComunidadAutonoma`. Si falta cualquier elemento, aborta con error en el log sin ejecutar escrituras ni DDL.
6. **Transacción única por fuente:**
   - Asegura las filas necesarias en `TiempoHorario` (lectura por rango `BETWEEN`, `INSERT` únicamente de horas faltantes y relectura de `idTiempo` desde BBDD).
   - Obtiene `idCCAA` (si aplica) y ejecuta `MERGE INTO` por lotes en la tabla de hechos.
   - Ejecuta `COMMIT` al final.
   - Si falla con `ORA-00001` (concurrencia en `TiempoHorario` o clave única) o `ORA-00060` (deadlock), hace `ROLLBACK` y reintenta la transacción completa hasta **3 intentos**.
   - Ante cualquier otro error, hace `ROLLBACK`, registra el error en log y vuelve al flujo normal sin propagar excepciones.

---

## 4. Mapeo JSON → tabla → campo y agregación horaria

Todas las fuentes se agregan a **hora UTC truncada** (`fecHora` naive en UTC) para respetar la granularidad de `TiempoHorario` y las claves únicas `UNIQUE(idTiempo, idCCAA)` y `UNIQUE(idTiempo, tipMercado)`. Los datos originales de 5 y 15 minutos permanecen íntegros en los JSON de `data/raw/`.

### 4.1 Dimensión `TiempoHorario`
| Columna | Tipo Oracle | Cálculo |
| :--- | :--- | :--- |
| `idTiempo` | `NUMBER(19)` | Si ya existe `fecHora`, se reutiliza el `idTiempo` de BBDD; si falta, entero `YYYYMMDDHH` de la hora UTC (ej. `2026-10-27 23:00Z` → `2026102723`). |
| `fecHora` | `TIMESTAMP` | Hora UTC truncada (`minute=0, second=0, microsecond=0`), naive. |
| `fecha` | `DATE` | Fecha local de `fecHora` en `CALENDAR_TZ`. |
| `hora` | `NUMBER(2)` | Hora local `0–23` en `CALENDAR_TZ`. |
| `diaSemana` | `NUMBER(1)` | Día ISO local `1–7` (`isoweekday()`). |
| `mes`, `year` | `NUMBER(2)` / `NUMBER(4)` | Mes (`1–12`) y año locales. |
| `indFinSemana` | `NUMBER(1)` | `1` si `diaSemana` es `6` o `7`; si no, `0`. |
| `indFestivo` | `NUMBER(1)` | `1` si existe fila en `FestivosBOE` con `UPPER(TRIM(ambito)) = 'NACIONAL'` para esa fecha local; si no, `0`. |

### 4.2 REE (`ree_esios_*.json`) → `DemandaGeneracionREE`
- **Origen:** `payload.included[*]`, comparando `type.strip().lower()`.
- **Agregación y calidad:** Parsea `datetime` ISO 8601 con offset → UTC → deduplica instantes exactos dentro de cada serie → valida rango `[15000, 45000]` MW por punto (parametrizable vía `REE_DEMAND_MIN_MW` / `REE_DEMAND_MAX_MW`). La media `round(..., 4)` solo es válida si la hora reúne exactamente **12/12 puntos**; si no, la columna queda en `NULL` y se registra hora parcial. Se crea fila si al menos una de las 4 series tiene valor válido.

| Serie REE (`type`) | Columna destino | Tipo Oracle | Notas |
| :--- | :--- | :--- | :--- |
| `Real` | `demandaRealMW` | `NUMBER(12, 4)` | Hora en curso queda parcial → `NULL` hasta la siguiente ingesta. |
| `Prevista` | `demandaPrevistaREEMW` | `NUMBER(12, 4)` | — |
| `Programada` | `demandaProgramadaMW` | `NUMBER(12, 4)` | — |
| `Programada total` | `demandaProgramadaTotalMW` | `NUMBER(12, 4)` | — |
| — | `idCCAA` | `NUMBER(10)` | Consultado en `ComunidadAutonoma` por `codIne = '00'`. |
| — | `genEolicaMW`, `genSolarMW`, `genHidraulicaMW`, `genNuclearMW`, `genCicloCombinadoMW` | `NUMBER(12, 4)` | Omitidos en `INSERT`/`UPDATE` (permanecen `NULL`). |

### 4.3 OMIE (`omie_*.json`) → `PreciosMercadoOmie`
- **Origen:** `records[] = {year, month, day, hour, price_spain, price_portugal}` donde `hour` es el periodo de 15 minutos (`1–96`, `92` o `100` en cambios horarios).
- **Agregación y calidad:** Inicio del periodo = medianoche local `(year, month, day)` en `Europe/Madrid` convertida a UTC + `(hour - 1) × 15 min`. Agrupa por hora UTC; exige **4/4 periodos** válidos dentro del rango `[-500, 4000]` €/MWh (`OMIE_PRICE_MIN_EUR` / `OMIE_PRICE_MAX_EUR`), aplicando `round(..., 4)`. Si ambos precios faltan o son inválidos, no se escribe la hora.

| Campo JSON | Columna destino | Tipo Oracle | Notas |
| :--- | :--- | :--- | :--- |
| `price_spain` (media 4 periodos) | `precioMarginalES` | `NUMBER(10, 4)` | `NULL` si falta/inválido (conservando PT si fuera válido). |
| `price_portugal` (media 4 periodos) | `precioMarginalPT` | `NUMBER(10, 4)` | `NULL` si falta/inválido (conservando ES si fuera válido). |
| Fijo `'diario'` | `tipMercado` | `VARCHAR2(50)` | Siempre `'diario'`. |

### 4.4 Open-Meteo (`open_meteo_*.json`) → `Meteorologia`
- **Seguridad geográfica:** Comprueba `|latitude - 40.4176| <= 0.5` y `|longitude - (-3.7394)| <= 0.5`. Si se aleja más de `0.5°`, aborta sin escribir y loguea aviso.
- **Desambiguación DST:** Convierte `hourly.time` local usando `data["timezone"]` con `zoneinfo`; ante horas repetidas del cambio de octubre asigna `fold=0` a la primera aparición y `fold=1` a la segunda.
- **Unidades:** Se conservan tal cual (km/h en viento, °C en temperatura, % en nubosidad/humedad, W/m² en radiación).

| Clave `hourly` | Columna destino | Tipo Oracle |
| :--- | :--- | :--- |
| `temperature_2m` | `temperatura_2m` | `NUMBER(5, 2)` |
| `relative_humidity_2m` | `humedad_relativa` | `NUMBER(3)` |
| `wind_speed_10m` / `80m` / `120m` / `180m` | `viento_10m` / `80m` / `120m` / `180m` | `NUMBER(5, 2)` |
| `wind_direction_10m` / `80m` / `120m` / `180m` | `viento_dir_10m` / `80m` / `120m` / `180m` | `NUMBER(5, 2)` |
| `cloud_cover` | `cobertura_nubes` | `NUMBER(3)` |
| `direct_normal_irradiance` | `radiacion_directa` | `NUMBER(8, 2)` |
| `shortwave_radiation` | `shortwave_radiation` | `NUMBER(8, 2)` |
| `global_tilted_irradiance` | `global_tilted_irradiance` | `NUMBER(8, 2)` |
| *(no presente en JSON)* | `temperaturaAparente` | `NUMBER(5, 2)` *(omitida → `NULL`)* |
| — | `idCCAA` | `NUMBER(10)` *(consulta `codIne = '13'`)* |

---

## 5. Decisiones de diseño

1. **Paquete separado `EcoGrid_API/oracle_store/`:** Desacoplado de FastAPI, APScheduler y conectores HTTP; los transformadores son funciones puras sin efectos secundarios ni dependencias de Oracle.
2. **Idempotencia estricta con `MERGE` + `COALESCE`:** Evita duplicados ante reejecuciones sobre un mismo JSON o solapamiento entre descargas consecutivas, y protege datos ya completos (ej. `demandaRealMW` no se borra si llega un `NULL` posterior).
3. **`cursor.setinputsizes(...)` explícito:** En `python-oracledb`, un `None` en la primera fila de `executemany` puede inferirse como `VARCHAR2` y fallar con `ORA-00932`/`DPY-3013`. Definir tipos bind antes de `executemany` previene fallos cuando hay horas parciales (`demandaRealMW=NULL`).
4. **Caché de guarda de esquema solo en éxito:** Si la primera validación de `USER_TAB_COLUMNS` falla (p. ej., BBDD aún sin crear), no se cachea para permitir que la app se recupere en cuanto el usuario ejecute el DDL sin reiniciar el servidor.
5. **Reutilización fiel de `TiempoHorario`:** Siempre se lee el diccionario `{fecHora: idTiempo}` directamente desde BBDD tras insertar las horas faltantes y nunca se actualizan filas previas de `TiempoHorario`.

---

## 6. Tablas que no se escriben y por qué

| Tabla | Estado | Motivo |
| :--- | :--- | :--- |
| `ComunidadAutonoma` | **Solo lectura** | Contiene catálogo maestro sembrado por el DDL; solo se consulta `idCCAA` por `codIne`. |
| `FestivosBOE` | **Solo lectura** | Se consulta por rango de fechas locales para calcular `indFestivo` en `TiempoHorario`. |
| `OfertaDemandaOmie` | **No se toca** | El JSON de OMIE descargado (`marginalpdbc`) solo contiene precios marginales, no curvas de oferta/demanda (`curva_pbc_uof`). |
| `PrediccionesDemanda`, `ModelosML`, `ImpactoDesviaciones`, `Alertas_operativas` | **No se tocan** | El formato definitivo de salida del pipeline ML aún no está cerrado. |
| `Usuarios`, `Roles`, `RedTransporte` | **No se tocan** | Pertenecen al backend de administración/seguridad y datos estructurales de red, fuera del alcance de la ingesta. |

---

## 7. Cómo probarlo

### 7.1 Suite de tests unitarios y de integración simulada (sin BBDD Oracle)
```powershell
cd EcoGrid_API
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 7.2 Simulación CLI (`--dry-run`, sin abrir conexión)
```powershell
cd EcoGrid_API
.\venv\Scripts\python.exe -m oracle_store.cli --file tests\fixtures\ree_esios_20261028_162855.json --dry-run
.\venv\Scripts\python.exe -m oracle_store.cli --file tests\fixtures\omie_20261028_162854.json --dry-run
.\venv\Scripts\python.exe -m oracle_store.cli --file tests\fixtures\open_meteo_20261028_162853.json --dry-run
```

### 7.3 Carga manual contra Oracle (cuando la BBDD exista)
```powershell
cd EcoGrid_API
.\venv\Scripts\python.exe -m oracle_store.cli --file data\raw\ree_esios_20261028_162855.json
```

### 7.4 Consultas SQL de verificación (en SQL Developer / SQLcl)
```sql
-- Conteo de filas cargadas por tabla
SELECT COUNT(*) AS total_horas FROM TiempoHorario;
SELECT COUNT(*) AS total_ree, MIN(t.fecHora) AS primera_utc, MAX(t.fecHora) AS ultima_utc
FROM DemandaGeneracionREE d JOIN TiempoHorario t ON t.idTiempo = d.idTiempo;
SELECT COUNT(*) AS total_omie FROM PreciosMercadoOmie WHERE tipMercado = 'diario';
SELECT COUNT(*) AS total_meteo FROM Meteorologia;

-- Verificar hora parcial REE (2026-10-28 15:00Z debe tener demandaRealMW NULL y previstas con valor)
SELECT t.fecHora, d.demandaRealMW, d.demandaPrevistaREEMW, d.demandaProgramadaMW, d.demandaProgramadaTotalMW
FROM DemandaGeneracionREE d
JOIN TiempoHorario t ON t.idTiempo = d.idTiempo
WHERE t.fecHora = TIMESTAMP '2026-10-28 15:00:00';

-- Verificar horas OMIE donde difieren España y Portugal
SELECT t.fecHora, p.precioMarginalES, p.precioMarginalPT
FROM PreciosMercadoOmie p
JOIN TiempoHorario t ON t.idTiempo = p.idTiempo
WHERE p.precioMarginalES <> p.precioMarginalPT
ORDER BY t.fecHora;
```

---

## 8. Errores habituales y solución

| Síntoma en log | Causa probable | Solución |
| :--- | :--- | :--- |
| `Persistencia Oracle omitida (...): faltan variables de conexión (...)` | `.env` sin credenciales Oracle o BBDD aún no configurada. | Comportamiento esperado mientras no haya BBDD; configurar `ORACLE_*` en `EcoGrid_API/.env` cuando exista. |
| `Persistencia Oracle abortada: Guarda de esquema Oracle fallida en USER_TAB_COLUMNS` | Falta ejecutar `crearTablasBBDDEcoGrid_v3.sql` o se conecta con un usuario distinto al propietario del esquema. | Ejecutar `crearTablasBBDDEcoGrid_v3.sql` con el usuario indicado en `ORACLE_USER` (ej. `ECOGRID`). |
| `ComunidadAutonoma no contiene los codIne requeridos: 00, 13` | No se ejecutó el bloque `5) Datos semilla` del script SQL. | Ejecutar los `INSERT INTO ComunidadAutonoma ...` y `COMMIT;` del DDL. |
| `DPY-6005` / `ORA-12170` / Timeout | ACL de Autonomous Database bloqueando la IP pública, `ORACLE_DSN` incorrecto o wallet incompleto. | Revisar lista blanca IP (ACL) en OCI, validar alias en `tnsnames.ora` y que `ORACLE_WALLET_DIR` tenga `tnsnames.ora`, `ewallet.p12`/`cwallet.sso` y `sqlnet.ora`. |
| `DPY-4011` o error de contraseña de wallet | `ORACLE_WALLET_PASSWORD` incorrecta o falta `cwallet.sso`. | Verificar contraseña asignada al descargar el wallet en OCI. |
| `ORA-01017: invalid username/password` | Credenciales incorrectas en `ORACLE_USER` / `ORACLE_PASSWORD`. | Corregir en `.env` (no usar `ADMIN` para la app; verificar usuario de aplicación). |

---

## 9. Seguridad

- **Cero secretos en repositorio:** `EcoGrid_API/.env`, carpetas de wallet (`wallet/`, `*wallet*/`) y ficheros de wallet (`*.sso`, `ewallet.p12`, `ewallet.pem`, `tnsnames.ora`, `sqlnet.ora`, `ojdbc.properties`) están excluidos en `.gitignore` tanto en la raíz como en `EcoGrid_API/.gitignore`.
- **Logs saneados:** Solo se registra `usuario` y `dsn` (alias de servicio). `OracleConfig` marca `password` y `wallet_password` con `field(repr=False)`.
- **SQL seguro:** Todas las sentencias usan variables bind (`:param`) sin interpolación ni concatenación de valores externos.
- **Sin DDL automático:** El paquete nunca ejecuta `CREATE`, `ALTER`, `DROP` ni `TRUNCATE`.

---

## 10. Pendientes y limitaciones conocidas

1. **Base de datos pendiente de creación:** El usuario debe ejecutar `EcoGrid_API/crearTablasBBDDEcoGrid_v3.sql` en Oracle 21c / Autonomous Database (y crear el usuario de esquema ej. `ECOGRID`), descomprimir el wallet fuera del repo y completar `EcoGrid_API/.env`, además de ejecutar una prueba real de conexión/ingesta end-to-end.
2. **Formato REE autenticado con token ESIOS V2 (`api.esios.ree.es`):** Cuando `ESIOS_API_TOKEN` está configurado, [`REEClient._fetch_from_esios`](file:///c:/Users/USER/Desktop/EcoGrid-Analytics/EcoGrid_API/src/connectors/ree_client.py#L54-L129) guarda `{ "payload": { "indicator": { "values": [...] } } }` (solo indicador 1293, sin `payload.included[*]`). Como ese esquema JSON no está cubierto por la especificación actual, `transform_ree` registra aviso y no inserta filas para ese formato hasta definirlo.
3. **Versiones de previsiones REE (`demandaPrevistaREEMW`):** Si futuras ingestas traen nuevas revisiones de previsión para una hora ya persistida con valor no nulo, `COALESCE(nuevo, actual)` actualiza con el nuevo valor no nulo (última ingesta prevalece); no se almacena historial de versiones de previsión porque el esquema tiene clave única `(idTiempo, idCCAA)`.
4. **Columnas sin fuente en los JSON actuales:**
   - `DemandaGeneracionREE`: `genEolicaMW`, `genSolarMW`, `genHidraulicaMW`, `genNuclearMW`, `genCicloCombinadoMW` permanecen en `NULL`.
   - `Meteorologia`: `temperaturaAparente` permanece en `NULL` (Open-Meteo no solicita `apparent_temperature`).
5. **`indFestivo` en `TiempoHorario`:** `FestivosBOE` nace vacía en `crearTablasBBDDEcoGrid_v3.sql`, por lo que `indFestivo` se insertará como `0`. Al no actualizarse filas ya existentes en `TiempoHorario`, si se cargan festivos posteriormente solo afectarán a horas aún no insertadas en `TiempoHorario` (salvo recarga/actualización manual).
6. **Datos previos en `EcoGrid_API/data/raw/`:** Los JSON descargados con anterioridad no se cargan automáticamente en bucle; pueden cargarse puntualmente mediante `python -m oracle_store.cli --file <ruta_json>`.

