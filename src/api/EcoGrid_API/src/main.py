"""
Punto de entrada principal de la aplicación FastAPI EcoGrid Analytics.
Expone la interfaz web Jinja2, endpoints REST de ingesta y módulo planificador (APScheduler).
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.config.settings import BASE_DIR, DATA_RAW_DIR, HOST, PORT, ESIOS_API_TOKEN
from src.services.ingestion_service import IngestionService
from src.services.scheduler_service import SchedulerService

app = FastAPI(
    title="EcoGrid Analytics API",
    description="Panel y API gestora de ingesta de datos meteorológicos y energéticos (Open-Meteo, OMIE, REE/ESIOS) con Automatizador de Tareas",
    version="1.1.0"
)

# Configuración de rutas estáticas y plantillas Jinja2
STATIC_DIR = BASE_DIR / "src" / "static"
TEMPLATES_DIR = BASE_DIR / "src" / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Instancias globales de servicios
ingestion_service = IngestionService(raw_dir=DATA_RAW_DIR)
scheduler_service = SchedulerService(
    config_path=BASE_DIR / "config" / "tasks.yaml",
    raw_dir=DATA_RAW_DIR
)

# Modelos Pydantic para peticiones
class ToggleSourceRequest(BaseModel):
    active: Optional[bool] = None

class ToggleTaskRequest(BaseModel):
    enabled: Optional[bool] = None

class UpdateTaskRequest(BaseModel):
    interval_minutes: int

# Ciclo de vida del planificador en segundo plano
@app.on_event("startup")
async def startup_event():
    """Inicia el motor planificador en segundo plano al arrancar la app."""
    scheduler_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Detiene el motor planificador limpiamente al detener la app."""
    scheduler_service.stop()

# --- Rutas de Vista HTML ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Renderiza el panel de control web principal de EcoGrid."""
    sources = ingestion_service.get_sources()
    raw_files = ingestion_service.list_raw_files()
    total_size = sum(f["size_bytes"] for f in raw_files)
    scheduled_tasks = scheduler_service.get_tasks()
    scheduler_status = scheduler_service.get_scheduler_status()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sources": sources,
            "raw_files": raw_files,
            "total_files": len(raw_files),
            "total_size_formatted": ingestion_service._format_size(total_size),
            "esios_token_configured": bool(ESIOS_API_TOKEN and ESIOS_API_TOKEN != "tu_token_aqui"),
            "scheduled_tasks": scheduled_tasks,
            "scheduler_status": scheduler_status
        }
    )

# --- Endpoints REST API de Ingesta Manual (Existentes e Intactos) ---

@app.get("/api/sources")
async def get_sources():
    """Retorna el catálogo completo de fuentes y su estado actual."""
    return {"sources": ingestion_service.get_sources()}

@app.post("/api/sources/{source_id}/toggle")
async def toggle_source(source_id: str, payload: Optional[ToggleSourceRequest] = None):
    """Activa o desactiva dinámicamente un origen de datos."""
    try:
        active_val = payload.active if payload else None
        updated = ingestion_service.toggle_source(source_id, active_val)
        return {
            "success": True,
            "message": f"Fuente '{source_id}' {'activada' if updated['active'] else 'desactivada'}",
            "source": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/sources/{source_id}/execute")
async def execute_source(source_id: str):
    """Ejecuta la ingesta manual de una fuente específica y guarda el archivo bruto."""
    try:
        result = ingestion_service.execute_source(source_id)
        return {
            "success": result["success"],
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la ejecución: {str(e)}")

@app.post("/api/ingestion/execute-active")
async def execute_active_sources():
    """Ejecuta la ingesta simultánea de todos los orígenes marcados como activos."""
    try:
        results = ingestion_service.execute_active_sources()
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "total_executed": len(results),
            "total_success": success_count,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en ingesta activa: {str(e)}")

@app.get("/api/raw-files")
async def list_raw_files():
    """Lista todos los archivos guardados en data/raw/ con sus metadatos."""
    files = ingestion_service.list_raw_files()
    total_size = sum(f["size_bytes"] for f in files)
    return {
        "total_files": len(files),
        "total_size_bytes": total_size,
        "total_size_formatted": ingestion_service._format_size(total_size),
        "files": files
    }

@app.get("/api/raw-files/{filename}")
async def get_raw_file(filename: str):
    """Obtiene el contenido y resumen del archivo bruto para previsualización."""
    try:
        data = ingestion_service.get_raw_file_content(filename)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer archivo: {str(e)}")

@app.get("/api/raw-files/{filename}/download")
async def download_raw_file(filename: str):
    """Descarga el archivo físico en bruto."""
    safe_name = Path(filename).name
    file_path = DATA_RAW_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    media_type = "application/json" if safe_name.endswith(".json") else "text/plain"
    return FileResponse(path=str(file_path), filename=safe_name, media_type=media_type)

@app.delete("/api/raw-files/{filename}")
async def delete_raw_file(filename: str):
    """Elimina un archivo bruto de data/raw/."""
    try:
        deleted = ingestion_service.delete_raw_file(filename)
        if not deleted:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return {"success": True, "message": f"Archivo '{filename}' eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Retorna estadísticas globales para el panel."""
    sources = ingestion_service.get_sources()
    raw_files = ingestion_service.list_raw_files()
    total_size = sum(f["size_bytes"] for f in raw_files)
    active_sources_count = sum(1 for s in sources if s["active"])
    
    return {
        "total_sources": len(sources),
        "active_sources": active_sources_count,
        "total_raw_files": len(raw_files),
        "total_size_bytes": total_size,
        "total_size_formatted": ingestion_service._format_size(total_size),
        "esios_token_configured": bool(ESIOS_API_TOKEN and ESIOS_API_TOKEN != "tu_token_aqui"),
        "scheduler": scheduler_service.get_scheduler_status()
    }

# --- Nuevos Endpoints Complementarios del Automatizador (APScheduler) ---

@app.get("/api/scheduler/tasks")
async def get_scheduled_tasks():
    """Retorna la lista completa de tareas programadas con sus intervalos y próximas ejecuciones."""
    return {
        "status": scheduler_service.get_scheduler_status(),
        "tasks": scheduler_service.get_tasks()
    }

@app.post("/api/scheduler/tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str, payload: Optional[ToggleTaskRequest] = None):
    """Activa o desactiva dinámicamente una tarea programada."""
    try:
        enabled_val = payload.enabled if payload else None
        updated = scheduler_service.toggle_task(task_id, enabled_val)
        return {
            "success": True,
            "message": f"Tarea '{task_id}' {'activada' if updated['enabled'] else 'desactivada'}",
            "task": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar estado de tarea: {str(e)}")

@app.post("/api/scheduler/tasks/{task_id}/update")
async def update_scheduled_task(task_id: str, payload: UpdateTaskRequest):
    """Modifica la frecuencia en minutos de una tarea programada y actualiza tasks.yaml."""
    try:
        updated = scheduler_service.update_task_interval(task_id, payload.interval_minutes)
        return {
            "success": True,
            "message": f"Frecuencia de '{task_id}' actualizada a {payload.interval_minutes} minutos",
            "task": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar intervalo: {str(e)}")

@app.post("/api/scheduler/tasks/{task_id}/execute")
async def execute_scheduled_task_now(task_id: str):
    """Dispara inmediatamente la ejecución manual de una tarea programada sin esperar al temporizador."""
    try:
        result = scheduler_service.execute_task_now(task_id)
        return {
            "success": result["success"],
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la ejecución de la tarea: {str(e)}")

@app.get("/api/scheduler/config-yaml")
async def get_scheduler_config_yaml():
    """Retorna el contenido en bruto de tasks.yaml para inspección técnica."""
    yaml_path = BASE_DIR / "config" / "tasks.yaml"
    if yaml_path.exists():
        return {"content": yaml_path.read_text(encoding="utf-8")}
    return {"content": ""}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=HOST, port=PORT, reload=True)
