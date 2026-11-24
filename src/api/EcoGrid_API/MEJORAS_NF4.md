# Mejoras técnicas aplicadas — NF4

## Objetivo

Este documento explica las mejoras técnicas aplicadas a `src/api/EcoGrid_API` para evolucionar el entregable y mantener trazabilidad entre datos, predicción y documentación.

## Salud y accesibilidad

Se han añadido los endpoints:

- `GET /health`: estado básico de FastAPI y scheduler.
- `GET /api/health`: alias de salud para scripts y automatización.
- `GET /api/metrics`: contadores básicos de peticiones, ejecuciones e fallos en memoria.

Los contadores se reinician al reiniciar el proceso. Esta implementación es adecuada para demostración local y no sustituye Prometheus, Grafana o persistencia de métricas en un despliegue real.

## Logs y errores

FastAPI registra ahora método, ruta, código HTTP y tiempo de respuesta. Los errores internos no se devuelven al cliente; se registran en la consola mediante logs y la API responde con mensajes genéricos. Los servicios de ingesta mantienen los detalles técnicos de diagnóstico para logs locales.

## Validaciones

El endpoint de actualización de intervalos rechaza valores menores que uno. Las operaciones manuales identifican orígenes y tareas inexistentes. El servicio de predicción valida que existan datos históricos suficientes, alineados por hora, lag 24 h y lag 168 h, 24 predicciones finitas y no negativas.

## Autenticación de panel

La pantalla con usuario y contraseña `admin/admin` se ha eliminado. Era una comprobación exclusivamente JavaScript y no protegía la API ni los archivos. En local el panel permanece operativo sin afirmaciones falsas de autenticación. Para producción se requiere autenticación real en FastAPI o delante de él, preferiblemente integrada con Spring Security.

## Coordinación con Spring Boot

La arquitectura final prevista es:

1. FastAPI puerto 8000 ingiere y persiste datos.
2. Oracle mantiene los datos históricos.
3. Spring puerto 8080 expone demanda y recibe predicciones.
4. FastAPI consulta Spring, ejecuta XGBoost y envía exactamente 24 predicciones.
5. Spring persiste el lote y el dashboard muestra el resultado.

La API key de predicción debe coincidir en ambos servicios y almacenarse exclusivamente en archivos `.env` locales.

## Modelo y MLOps

El modelo actual es `models/modelo_xgboost_demanda.json`. Su identificador se configura con `PREDICTION_MODEL_ID` y el archivo con `PREDICTION_MODEL_PATH`.

El sistema evita ejecutar el modelo más de una vez cada 24 horas por éxito registrado en el estado del scheduler.

No se implementa retraining automático porque el proyecto no incluye todavía un pipeline completo de partición temporal, métricas fuera de muestra, registro de experimentos y promoción automática. Implementarlo sin esas garantías puede producir un modelo peor o datos no comparables. La evolución adecuada sería:

- Dataset versionado desde Oracle.
- Entrenamiento periódico fuera del proceso API.
- Validación temporal con MAE, RMSE y MAPE.
- Baseline explícita frente al modelo anterior.
- Registro de versión, hash, fecha y métricas.
- Promoción manual o automática solo si supera umbrales aprobados.

## Comandos exactos

```powershell
cd src\api\EcoGrid_API
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Comprobaciones:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/metrics
Invoke-RestMethod http://127.0.0.1:8000/api/sources
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/sources/open_meteo/execute
```
