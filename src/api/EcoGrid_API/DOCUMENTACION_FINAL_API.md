# EcoGrid Analytics API — Documentación técnica final

## Alcance

Este documento describe la parte Python de EcoGrid Analytics situada en `src/api/EcoGrid_API`. La API FastAPI gestiona fuentes externas, archivos brutos, persistencia Oracle, automatización y predicción XGBoost.

## Arquitectura

```text
Fuentes externas
Open-Meteo / OMIE / REE-ESIOS
          |
          v
FastAPI 127.0.0.1:8000
Conectores -> JSON bruto -> OracleStore
          |
          v
Oracle Autonomous Database
          |
          v
Spring Boot 127.0.0.1:8080
GET /api/demanda/historica
          |
          v
FastAPI XGBoost -> 24 predicciones
          |
          v
POST /api/predicciones/lote
          |
          v
Spring Boot / dashboard
```

## Componentes

- `src/main.py`: aplicación FastAPI, panel, endpoints, scheduler y endpoints de salud.
- `src/connectors/`: clientes HTTP de Open-Meteo, OMIE y REE/ESIOS.
- `src/services/ingestion_service.py`: descarga, archivo bruto y persistencia.
- `src/services/scheduler_service.py`: trabajos periódicos APScheduler.
- `src/services/prediction_service.py`: XGBoost y coordinación con Spring.
- `oracle_store/`: configuración, wallet Thin mTLS, transformaciones, MERGE y verificación.
- `config/tasks.yaml`: fuentes, intervalos y estado de tareas.
- `models/modelo_xgboost_demanda.json`: modelo XGBoost usado por la predicción.

## Configuración

Copiar `.env.example` a `.env` y completar solamente valores locales:

```powershell
Copy-Item .env.example .env
```

`.env` no debe enviarse al repositorio. Oracle se deshabilita por defecto con `ORACLE_ENABLED=false`. Las credenciales Oracle y el wallet deben permanecer fuera del repositorio.

Variables principales:

- `HOST`, `PORT`, `DATA_DIR`
- `ORACLE_ENABLED`, `ORACLE_USER`, `ORACLE_PASSWORD`
- `ORACLE_DSN`, `ORACLE_WALLET_DIR`, `ORACLE_WALLET_PASSWORD`
- `ESIOS_API_TOKEN`
- `SPRING_API_BASE_URL`, `SPRING_PREDICTIONS_API_KEY`
- `PREDICTION_MODEL_ID`, `PREDICTION_MODEL_PATH`

## Arranque

Desde la raíz del repositorio:

```powershell
cd src\api\EcoGrid_API
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Sin una base Oracle configurada, se puede arrancar con `ORACLE_ENABLED=false` y usar el panel y los conectores públicos.

## Comprobaciones

- Panel: <http://127.0.0.1:8000/>
- Salud FastAPI: <http://127.0.0.1:8000/health>
- Salud alternativa: <http://127.0.0.1:8000/api/health>
- OpenAPI: <http://127.0.0.1:8000/docs>
- Métricas básicas: <http://127.0.0.1:8000/api/metrics>
- Fuentes: <http://127.0.0.1:8000/api/sources>
- Tareas: <http://127.0.0.1:8000/api/scheduler/tasks>

Ejemplo:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/sources/ree_esios/execute
```

## Oracle

Oracle se utiliza con `python-oracledb` en modo Thin y wallet mTLS. El directorio del wallet debe contener los archivos de red propios y debe permanecer fuera del repositorio. Las operaciones de persistencia usan claves naturales y sentencias MERGE idempotentes.

Comandos válidos:

```powershell
python -m oracle_store.cli --file data\raw\archivo.json --dry-run
python -m oracle_store.cli --file data\raw\archivo.json --raise-on-error
python -m oracle_store.backfill --start-date 2026-10-29 --end-date 2026-11-12
python -m oracle_store.verify --since 2026-10-28T23:00:00
```

El comando antiguo `python -m oracle_store.cli execute --source ...` no es válido y no debe utilizarse.

## Predicción y Spring Boot

Spring Boot debe escuchar en el puerto 8080. FastAPI utiliza:

- `GET /api/demanda/historica?ccaaId=1&desde=...&hasta=...`
- `POST /api/predicciones/lote`

El segundo endpoint recibe `X-API-Key`. La clave configurada en FastAPI debe coincidir con `PREDICTIONS_API_KEY` del servicio Spring. Las predicciones se generan a partir de 24 horas anteriores y 168 horas anteriores.

El dashboard final depende de Spring, Oracle y FastAPI: Spring obtiene los históricos desde Oracle, FastAPI genera el lote y Spring guarda y expone las predicciones.

## Seguridad

- No almacenar `.env`, wallets, tokens o contraseñas en Git.
- No incluir rutas absolutas ni contraseñas en documentación o ejemplos.
- El panel FastAPI es una herramienta operativa local; no sustituye una autenticación de producción.
- El login visual antiguo `admin/admin` se eliminó por no proporcionar seguridad real.
- Los errores HTTP internos deben ser genéricos y registrarse con trazas en logs locales.

## MLOps aplicable

- Salud básica de proceso y scheduler.
- Métricas básicas en memoria de peticiones y ejecuciones.
- Logs estructurados con tiempos de respuesta.
- Validación de 24 predicciones, valores finitos y no negativos.
- Versionado del modelo mediante el archivo JSON y `PREDICTION_MODEL_ID`.
- El retraining automático no se aplica por falta de pipeline reproducible de evaluación histórica, coste operativo y dependencia de datos Oracle/Spring; una evolución futura requeriría dataset versionado, métricas MAE/RMSE/MAPE, partición temporal y promoción controlada del modelo.