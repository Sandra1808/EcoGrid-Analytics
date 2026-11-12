# DOCUMENTACIÓN TÉCNICA FINAL – EcoGrid Analytics API

> **Objetivo** – Este documento describe de forma exhaustiva la arquitectura, tecnologías, flujo de datos y proceso de despliegue de la API **EcoGrid Analytics**. Está pensado para ser entregado como proyecto final y servir de referencia a evaluadores, profesores o futuros desarrolladores.

---

## 1. Arquitectura de la API y Estructura del Proyecto

```
EcoGrid-Analytics/
└─ src/
   └─ EcoGrid_API/
      ├─ config/                 # Configuración estática (tasks.yaml, settings.py)
      ├─ data/
      │   └─ raw/                # JSONs descargados por los conectores (persistencia en disco)
      ├─ oracle_store/            # Capa de persistencia Oracle
      │   ├─ __init__.py
      │   ├─ config.py           # Lectura de .env y dataclass OracleConfig
      │   ├─ connection.py       # Conexión Thin mTLS a Autonomous DB
      │   ├─ time_dimension.py   # Gestión de tabla TiempoHorario
      │   ├─ transformers.py     # Transformadores puros (REE, OMIE, Open‑Meteo)
      │   ├─ repository.py       # Sentencias MERGE idempotentes y consultas auxiliares
      │   ├─ service.py          # Orquestación (modo dual raise_on_error)
      │   ├─ cli.py              # CLI para backfill, dry‑run y pruebas manuales
      │   ├─ backfill.py         # Motor de backfill histórico parametrizable
      │   └─ verify.py           # Verificador de continuidad horaria
      ├─ src/                     # Código de la aplicación FastAPI
      │   ├─ __init__.py
      │   ├─ main.py              # Punto de entrada, enrutado FastAPI, Jinja2
      │   ├─ config/
      │   │   ├─ __init__.py
      │   │   └─ settings.py      # Rutas, host/port, ESIOS token, carpetas
      │   ├─ connectors/
      │   │   ├─ __init__.py
      │   │   ├─ meteo_client.py   # Open‑Meteo
      │   │   ├─ omie_client.py    # OMIE
      │   │   └─ ree_client.py     # REE / ESIOS
      │   ├─ services/
      │   │   ├─ __init__.py
      │   │   ├─ ingestion_service.py   # Lógica de descarga, guardado en data/raw, triggers
      │   │   ├─ scheduler_service.py   # APScheduler wrapper
      │   │   └─ prediction_service.py   # Predicción de demanda con XGBoost + Spring
      │   ├─ static/            # CSS / JS para el panel web
      │   └─ templates/         # Jinja2 templates (index.html, …)
      ├─ models/                # Modelo XGBoost (modelo_xgboost_demanda.json)
      ├─ tests/                 # Unit‑/integración tests
      ├─ scripts/               # Scripts auxiliares (backfill_ree.py, verify_ree_range.py)
      ├─ .env.example           # Plantilla de variables de entorno (no versionada)
      └─ DOCUMENTACION_FINAL_API.md   # **Este documento**
```

### Responsabilidades de los componentes principales
| Componente | Responsabilidad |
|------------|-----------------|
| **FastAPI (`src/main.py`)** | Punto de entrada, exposición de endpoints HTTP, renderizado del panel web con Jinja2, arranque y parada del `SchedulerService`. |
| **Connectors (`src/connectors/*.py`)** | Clientes HTTP específicos para cada fuente externa (Open‑Meteo, OMIE, REE/ESIOS). Manejan peticiones, parsing JSON y gestión de errores de red. |
| **IngestionService (`src/services/ingestion_service.py`)** | Orquesta la descarga, guardado bruto en `data/raw/`, transformación mediante `oracle_store.transformers`, y delega la persistencia a `OracleService`. Provee APIs internas usadas por los endpoints y por el scheduler. |
| **SchedulerService (`src/services/scheduler_service.py`)** | Wrapper de APScheduler. Lee `config/tasks.yaml`, registra jobs (`open_meteo_madrid`, `omie_marginal_prices`, `ree_demanda_tiempo_real`), permite activar/desactivar tareas vía API y expone estado del planificador. |
| **Oracle Store (`oracle_store/`)** | • `config.py`: carga segura de variables de entorno (`OracleConfig`).<br>• `connection.py`: crea la conexión Thin mTLS a la Autonomous DB usando `wallet_dir` y `wallet_password`.<br>• `repository.py`: operaciones `MERGE INTO` idempotentes, consultas de dimensión temporal, registro de estadísticas de filas insertadas/actualizadas.<br>• `service.py`: capa de alto nivel que combina transformación y persistencia; modo dual (`raise_on_error=False` para ingestión automática, `True` para backfill/CLI). |
| **Transformers (`oracle_store/transformers.py`)** | Funciones puras que convierten los JSON descargados a estructuras listas para `INSERT/MERGE` (agregación horaria, manejo de DST, validaciones de rango). |
| **Backfill & Verify (`oracle_store/backfill.py`, `verify.py`)** | Motor de carga histórica parametrizable y script de verificación de continuidad horaria. |
| **Prediction Service (`src/services/prediction_service.py`)** | Genera pronósticos de demanda a 24 h usando un modelo XGBoost entrenado. Consume el endpoint Spring `/api/demanda/historica`, crea features horarias, lag 24 h y lag 168 h, y envía el payload con `modeloId`, `predicciones` y `demandaBaselineMw` al micro‑servicio Spring. |
| **Templates / Static** | UI del panel web que muestra fuentes, archivos brutos, estado del scheduler y métricas. |

---

## 2. Tecnologías Usadas y Justificación (Python / FastAPI)

| Tecnología | Versión (según `requirements.txt`) | Justificación |
|------------|------------------------------------|--------------|
| **Python 3.11** | 3.11.x | Lenguaje de alto nivel con gran ecosistema científico (pandas, numpy, scikit‑learn, XGBoost). Permite desarrollo rápido y legible. |
| **FastAPI** | >=0.100.0 | Framework ASGI que combina **rendimiento comparable a Node/Go** (Uvicorn) con **tipado estático** (Pydantic) y generación automática de OpenAPI. Ideal para micro‑servicios REST que necesitan alta concurrencia (descargas paralelas). |
| **Uvicorn** | >=0.22.0 | Servidor ASGI ligero y rápido; permite recarga (`--reload`) durante desarrollo. |
| **APScheduler** | >=3.10.0 | Scheduler de tareas en proceso; fácil integración con FastAPI y permite cron‑style jobs sin depender de cron externo. |
| **python‑oracledb** | >=2.0.0 | Cliente oficial de Oracle; modo *Thin* elimina la necesidad de Instant Client, facilitando la instalación en entornos CI/CD. |
| **pandas** | >=2.0.0 | Manipulación de series temporales y agregaciones (p.ej., promedio de 12 puntos REE por hora). |
| **httpx / requests** | – | Cliente HTTP sin bloqueo (httpx) o sin bloqueo opcional para simplificar código. |
| **python‑dotenv** | >=1.0.0 | Carga de variables de entorno desde `.env` de forma segura. |
| **Jinja2** | >=3.1.2 | Plantillas para el panel de control web integrado en la API. |
| **pytest** | – | Framework de pruebas unitarias e integración. |
| **xgboost** | 3.4.1 | Modelo de machine‑learning utilizado para la predicción de demanda eléctrica a 24 h. |
| **joblib** | >=1.3.0 | Serialización de modelos y objetos de Python (usado por XGBoost). |
| **numpy** | >=1.24.0 | Operaciones numéricas y soporte a pandas/XGBoost. |
| **scikit-learn** | >=1.3.0 | Herramientas auxiliares para pre‑procesado y métricas de modelo. |

### Por qué Python + FastAPI
1. **Asincronía nativa** – FastAPI y httpx permiten lanzar varias descargas simultáneas (ej. REE cada 30 min, OMIE cada hora) sin bloquear el event loop.
2. **Facilidad de integración con ciencia de datos** – Pandas, NumPy, XGBoost y future ML pipelines pueden reutilizarse directamente sobre los datos que ya llegan a la API.
3. **Desarrollo rápido y tipado** – Con Pydantic los esquemas de entrada/salida están validados automáticamente, reduciendo errores de serialización.
4. **Documentación automática** – Swagger UI y Redoc se generan a partir de los mismos tipos, lo que facilita la entrega académica.
5. **Ligereza** – El stack tiene < 30 MB de dependencias principales, se ejecuta en cualquier entorno con Python 3.11.
6. **Compatibilidad con Oracle Thin** – `python-oracledb` funciona sin bibliotecas nativas, evitando la complejidad de instalar Instant Client en los equipos de los evaluadores.

---

## 3. Conexión con las APIs Externas

| Fuente | Cliente | URL base | Principales parámetros | Manejo de respuesta |
|--------|----------|----------|------------------------|----------------------|
| **Open‑Meteo** | `meteo_client.py` | `https://api.open-meteo.com/v1/forecast` | `latitude`, `longitude`, `hourly` (windspeed_10m, winddirection_10m, radiation, cloudcover), `timezone=Europe/Madrid` | La respuesta JSON se descarga con `httpx.get`. Se valida el código de estado (200) y se extraen los arrays horarios. Los datos se guardan tal cual en `data/raw/` y luego `transformers.aggregate_meteo` los convierte a filas por hora. |
| **OMIE** | `omie_client.py` | `https://www.omie.es/es/file-download` (ejemplo) | Parámetro `market=MIBEL`, `file_parent=marginalpdbc` | Se realiza una petición GET con token de autorización opcional. El CSV/JSON devuelto se parsea y se agrupa por hora (media de los 4 intervalos). Se guarda el archivo bruto y se transforma a `PreciosMercadoOmie`. |
| **REE / ESIOS** | `ree_client.py` | `https://api.esios.ree.es/indicators/{indicator}` | `indicator_real=1293`, `indicator_forecast=460`, token ESIOS (opcional) | Se usa `httpx` con cabecera `Authorization: Bearer <token>`; si falla (token ausente o expirado) se intenta el endpoint público fallback. Los 12 valores de 5 min por hora se promedian (round 4) y se guarda el JSON bruto. |

### Lógica común en los clientes
1. **Construcción de URL** con los parámetros de configuración (`src/config/settings.py`).
2. **Petición HTTP** (asíncrona con `httpx.AsyncClient` cuando el `IngestionService` lo llama). Se captura `httpx.ConnectTimeout`, `httpx.HTTPStatusError` y se registra en los logs.
3. **Persistencia en disco** – El archivo se escribe bajo `data/raw/<source>_<timestamp>.json` manteniendo la estructura original para que el modelo de IA pueda reutilizarla.
4. **Devolución estructurada** – Cada cliente devuelve un `dict` con `raw_path`, `data` (payload parseado) y `metadata` (fecha y origen) que es consumido por `IngestionService`.

---

## 4. Funcionamiento de la Conexión con Oracle Autonomous Database

### 4.1 Proceso de conexión
1. **Carga de variables** – `OracleConfig.from_env()` lee del archivo `.env` (ubicado en `src/EcoGrid_API/.env`). Las variables críticas son:
   - `ORACLE_ENABLED`
   - `ORACLE_USER`
   - `ORACLE_PASSWORD`
   - `ORACLE_DSN`
   - `ORACLE_WALLET_DIR`
   - `ORACLE_WALLET_PASSWORD` (opcional si el wallet tiene `cwallet.sso`).
2. **Thin mode** – En `connection.connect_oracle` se establece `oracledb.defaults.thin_mode = True` para evitar la dependencia del *Instant Client*.
3. **Parámetros de conexión**
   ```python
   connection = oracledb.connect(
       user=config.user,
       password=config.password,
       dsn=config.dsn,
       config_dir=config.wallet_dir,
       wallet_location=config.wallet_dir,
       wallet_password=config.wallet_password or None,
       tcp_connect_timeout=config.connect_timeout,
   )
   ```
   - `config_dir` y `wallet_location` apuntan a la **ruta absoluta** del wallet proporcionada por el usuario (valor tomado del `.env`).
   - `wallet_password` sólo se envía si el wallet no contiene `cwallet.sso`.
4. **Reintentos** – Hasta 2 intentos con `retry_delay_seconds=0.5`. Sólo se vuelven a intentar errores transitorios (`_is_transient_connection_error`).
5. **Autocommit = False** – Se gestiona la transacción manualmente en `service.py` para asegurar atomicidad entre múltiples `MERGE`. 

### 4.2 Propósito de la capa Oracle
- **Persistencia estructurada** de los datos descargados: tablas de hechos (`DemandaGeneracionREE`, `PreciosMercadoOmie`, `Meteorologia`) y dimensión temporal (`TiempoHorario`).
- **Idempotencia** mediante `MERGE INTO` en `oracle_store.repository`. Cada inserción incluye la clave única (p.ej., `IDTIEMPO` + `IDCCAA`) y utiliza la cláusula `WHEN MATCHED THEN UPDATE` para actualizar los valores sin crear duplicados.
- **Validación de esquema** – `verify_schema` comprueba que todas las columnas requeridas existen y que los códigos INE de comunidades autónomas están presentes, abortando la ejecución con un error descriptivo si algo falta.
- **Modo dual de errores** – Cuando la API se ejecuta de forma programada (`SchedulerService`) se llama a `persist_to_oracle(..., raise_on_error=False)`. Los fallos se registran como advertencias y la ingestión continúa. En backfill o CLI (`raise_on_error=True`) los errores se propagan y el proceso termina con traceback, lo que permite al usuario ver exactamente qué falló.

---

## 5. Flujo Completo de la API y Capacidades del Sistema

1. **Scheduler arranca** (`startup_event`) → `SchedulerService` lee `config/tasks.yaml` y registra los jobs.
2. **Job disparado** (cron o ejecución manual vía endpoint `/api/sources/{id}/execute`).
3. **IngestionService** solicita al *connector* correspondiente descargar los datos.
4. **Connector** devuelve JSON bruto → se guarda en `data/raw/` con nombre `<source>_<yyyyMMdd_HHmmss>.json`.
5. **Transformadores** (`oracle_store.transformers`) convierten los datos a estructuras de tabla:
   - *REE*: promedio de 12 lecturas de 5 min → demanda real por hora.
   - *OMIE*: promedio de 4 lecturas por hora → precios marginales.
   - *Open‑Meteo*: valores directos por hora.
6. **OracleService** (`oracle_store.service.persist_to_oracle`) abre una transacción, llama a `repository.merge_*` para cada tabla, registra cuántas filas fueron **insertadas** y cuántas **actualizadas**.
7. **Commit / Rollback** – Si `raise_on_error=False` y ocurre un error, se hace `rollback` y se escribe un warning; si es `True`, el error se propaga.
8. **Resultado** – Se devuelve al cliente (API o CLI) un objeto con:
   ```json
   {
     "status": "SUCCESS",
     "rows_inserted": 24,
     "rows_updated": 0,
     "message": "Persistencia completada"
   }
   ```
9. **Panel web** (`/`) muestra:
   - Estado de cada fuente (activa/inactiva).
   - Lista de archivos en `data/raw/` (tamaño, fecha).
   - Estado del scheduler (running, next runs).
   - Métricas resumidas (total archivos, tamaño total, fuentes activas).
10. **Funcionalidades extra**
    - **Backfill histórico** (`oracle_store.backfill`) con parámetros `--start-date` / `--end-date`.
    - **Verificación de continuidad** (`oracle_store.verify`) que asegura que no haya huecos en `TiempoHorario`.
    - **Modo dry‑run** (`oracle_store.cli --dry-run`) para probar la lógica sin tocar la BD.
    - **Toggle de fuentes y tareas** vía API (`/api/sources/{id}/toggle`, `/api/tasks/{id}/toggle`).
    - **Descarga / borrado** de archivos brutos a través de los endpoints `/api/raw-files/...`.
    - **Predicción de demanda** (ver sección 5.2).

### 5.2 Predicción de demanda con XGBoost y Spring
- **Servicio**: `src/services/prediction_service.py` implementa `DailyPredictionService`.
- **Variables de entorno requeridas**:
  - `SPRING_API_BASE_URL` – URL base del micro‑servicio Spring que expone `/api/demanda/historica`.
  - `SPRING_PREDICTIONS_API_KEY` – Token de autorización para el endpoint Spring.
  - `PREDICTION_MODEL_PATH` – Ruta al modelo XGBoost (`models/modelo_xgboost_demanda.json`).
  - `PREDICTION_MODEL_ID` – Identificador del modelo registrado en el catálogo de modelos del servicio Spring.
- **Flujo**:
  1. Se consulta la demanda histórica a Spring (últimos 9 días).
  2. Se construyen features horarias, sinusoidales y lags (`lag_24h`, `lag_168h`).
  3. Se carga el modelo XGBoost (`xgb.XGBRegressor`) y se generan 24 predicciones horarias.
  4. Se empaqueta el payload con `modeloId`, `predicciones` (timestamp, demandaPredichaMw, demandaBaselineMw) y se envía al endpoint Spring de predicciones.
- **Modo de error**: si falta alguna variable de entorno o el modelo no está disponible, la clase lanza `RuntimeError` con mensaje descriptivo.

---

## 6. Guía Técnica de Instalación, Montaje y Ejecución (Para Evaluadores)

> **Requisitos previos** – Windows 10/11 con PowerShell, Python 3.11+. Acceso a la Autonomous Oracle Database y al archivo *wallet* que se haya recibido en el proyecto. Además, disponer del modelo XGBoost en `models/` y, opcionalmente, del micro‑servicio Spring para la predicción.

### 6.1 Clonar el repositorio
```powershell
git clone https://github.com/tu-usuario/EcoGrid-Analytics.git
cd EcoGrid-Analytics\src\EcoGrid_API
```

### 6.2 Crear y activar el entorno virtual
```powershell
# Evitar la política de ejecución restrictiva (solo la primera vez)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

python -m venv venv
# Activar
.\venv\Scripts\Activate.ps1   # PowerShell
# o bien
.\venv\Scripts\activate.bat   # CMD
```

### 6.3 Instalar dependencias
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```
> **Nota:** `python-oracledb` se instalará en modo *Thin* y no necesita Instant Client.

### 6.4 Configurar variables de entorno
1. Copia el archivo de ejemplo y adapta los valores:
```powershell
copy .env.example .env
notepad .env   # o tu editor favorito
```
2. Modifica al menos las siguientes líneas (ruta del wallet **local** a tu máquina) y añade las variables de predicción:
```dotenv
ORACLE_ENABLED=true
ORACLE_USER=ECOGRID
ORACLE_PASSWORD=TuContraseña
ORACLE_DSN=ecogriddb_low
ORACLE_WALLET_DIR=C:\\Users\\TuUsuario\\oracle_wallet   # <‑ carpeta donde descomprimiste el zip
ORACLE_WALLET_PASSWORD=Ec0gridwallet@   # solo si no usas cwallet.sso
CALENDAR_TZ=Europe/Madrid
NACIONAL_CCAA_CODINE=00
METEO_CCAA_CODINE=13
ESIOS_API_TOKEN=tu_token_esios_o_deja_vacio_para_fallback
SPRING_API_BASE_URL=http://127.0.0.1:8080   # ejemplo de micro‑servicio Spring
SPRING_PREDICTIONS_API_KEY=mi_api_key
PREDICTION_MODEL_PATH=models/modelo_xgboost_demanda.json
PREDICTION_MODEL_ID=1
```
3. **Importante:** el directorio indicado en `ORACLE_WALLET_DIR` debe contener `tnsnames.ora`, `cwallet.sso` (o `ewallet.p12`) y `sqlnet.ora`.

### 6.5 Ejecutar la API (modo desarrollo)
```powershell
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
- La terminal debe permanecer abierta; el `SchedulerService` se ejecuta en segundo plano dentro del mismo proceso.
- Accede a `http://127.0.0.1:8000/` para ver el panel de control.
- La documentación OpenAPI está disponible en `http://127.0.0.1:8000/docs`.

### 6.6 Ejecución de tareas manuales o backfill
- **Ejecutar una fuente puntual** (por ejemplo REE):
  ```powershell
  python -m src.main   # arranca la API y usa el endpoint /api/sources/ree_esios/execute
  # o directamente vía CLI interna
  python -m oracle_store.cli execute --source ree_esios
  ```
- **Backfill histórico** (REE desde 2026‑10‑29):
  ```powershell
  python -m oracle_store.backfill --start-date 2026-10-29 --end-date 2026-11-12
  ```
- **Verificación de continuidad**:
  ```powershell
  python -m oracle_store.verify --since 2026-10-28T23:00:00Z
  ```
- **Ejecutar predicción diaria** (requiere Spring disponible):
  ```powershell
  python -c "from src.services.prediction_service import DailyPredictionService; print(DailyPredictionService().predict_and_save())"
  ```

### 6.7 Desactivar el programador (si fuera necesario)
Edita `src/EcoGrid_API/config/tasks.yaml` y cambia `enabled: true` a `false` para la(s) tarea(s) que desees desactivar. Reinicia la API para que el cambio tenga efecto.

---

## 7. Referencias rápidas
| Archivo | Propósito |
|---------|-----------|
| `src/main.py` | Punto de entrada FastAPI, UI y registro del scheduler. |
| `src/config/settings.py` | Constantes de rutas, host/port, token ESIOS. |
| `src/connectors/*.py` | Clientes HTTP para cada fuente externa. |
| `src/services/ingestion_service.py` | Orquesta descarga → guardado bruto → transformación → persistencia. |
| `src/services/scheduler_service.py` | Lectura `tasks.yaml`, registro de jobs APScheduler, API de control. |
| `src/services/prediction_service.py` | Servicio de predicción diaria con XGBoost y Spring. |
| `oracle_store/config.py` | Lectura de .env y dataclass de configuración Oracle. |
| `oracle_store/connection.py` | Conexión Thin mTLS a Autonomous DB. |
| `oracle_store/repository.py` | Sentencias MERGE idempotentes y consultas auxiliares. |
| `oracle_store/service.py` | Persistencia con modo dual (silencioso vs. explícito). |
| `oracle_store/backfill.py` | Motor de backfill histórico parametrizable. |
| `oracle_store/verify.py` | Verificador de continuidad temporal. |
| `config/tasks.yaml` | Definición de tareas programadas (cron, intervalos, `enabled`). |
| `DOCUMENTACION_FINAL_API.md` | **Este documento** – guía completa para evaluadores. |

---

*Fin del documento.*