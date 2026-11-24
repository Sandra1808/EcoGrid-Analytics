# EcoGrid Analytics API

API FastAPI para ingesta de datos meteorológicos y eléctricos, persistencia en Oracle y coordinación de predicción con Spring Boot.

## Requisitos

- Windows 10/11
- Python 3.11 o 3.12
- Spring Boot opcional en el puerto 8080
- Oracle Autonomous Database y wallet propios solo para persistencia real

## Arranque desde cero

Desde la raíz del repositorio:

```powershell
cd src\api\EcoGrid_API
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura `.env` localmente. Para operar sin Oracle:

```dotenv
ORACLE_ENABLED=false
HOST=127.0.0.1
PORT=8000
DATA_DIR=data/raw
```

Arranca la API:

```powershell
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

## Comprobaciones

- Panel: `http://127.0.0.1:8000/`
- Estado: `http://127.0.0.1:8000/health`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Métricas básicas: `http://127.0.0.1:8000/api/metrics`
- Fuentes: `http://127.0.0.1:8000/api/sources`
- Tareas: `http://127.0.0.1:8000/api/scheduler/tasks`

Ejemplo PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/sources/open_meteo/execute
```

## Coordinación

- FastAPI usa el puerto 8000 y gestiona conectores, JSON bruto, scheduler y modelo XGBoost.
- Spring Boot usa el puerto 8080 y expone demanda histórica y recepción de predicciones.
- Oracle persiste datos fuente y predicciones; el wallet nunca debe copiarse al repositorio.
- El modelo consulta `GET /api/demanda/historica`, genera 24 horas y envía el lote a `POST /api/predicciones/lote` con `X-API-Key`.

Comandos Oracle seguros:

```powershell
python -m oracle_store.cli --file data\raw\archivo.json --dry-run
python -m oracle_store.cli --file data\raw\archivo.json --raise-on-error
python -m oracle_store.backfill --start-date 2026-10-29 --end-date 2026-11-12
python -m oracle_store.verify --since 2026-10-28T23:00:00
```

## Seguridad operativa

No subir `.env`, wallet, certificados, contraseñas ni claves API. `FastAPI` se considera local salvo que se añada autenticación y TLS delante. El login `admin/admin` se ha eliminado porque no proporcionaba autenticación real.

Consulte `DOCUMENTACION_FINAL_API.md` y `MEJORAS_NF4.md` para arquitectura, recorrido de datos y MLOps.