"""
Servicio del Automatizador y Planificador de Tareas (APScheduler Engine).
Gestiona la ejecución periódica y autónoma de los conectores de EcoGrid según tasks.yaml.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import logging
import yaml
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import BASE_DIR, DATA_RAW_DIR
from src.services.ingestion_service import IngestionService

logger = logging.getLogger("EcoGrid.Scheduler")

DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "tasks.yaml"
SCHEDULER_STATE_FILE = BASE_DIR / "data" / "scheduler_state.json"

class SchedulerService:
    """Motor orquestador y planificador autónomo de ingestas periódicas."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH, raw_dir: Path = DATA_RAW_DIR):
        self.config_path = config_path
        self.raw_dir = raw_dir
        self.ingestion_service = IngestionService(raw_dir=self.raw_dir)
        
        # Cargar configuración YAML
        self.config = self._load_config()
        tz_name = self.config.get("scheduler", {}).get("timezone", "Europe/Madrid")
        try:
            self.timezone = ZoneInfo(tz_name)
        except Exception:
            self.timezone = ZoneInfo("Europe/Madrid")

        # Inicializar BackgroundScheduler
        self.scheduler = BackgroundScheduler(timezone=self.timezone)
        self.task_states: Dict[str, Dict[str, Any]] = self._load_task_states()
        self._is_started = False

    def _load_config(self) -> Dict[str, Any]:
        """Carga el archivo tasks.yaml si existe, o retorna una plantilla segura."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.error(f"Error al leer {self.config_path}: {e}")

        # Retornar estructura por defecto si no existe
        return {
            "version": "1.0",
            "scheduler": {"timezone": "Europe/Madrid"},
            "tasks": {}
        }

    def _save_config(self) -> None:
        """Persiste la configuración actual de tareas en tasks.yaml."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, sort_keys=False, allow_unicode=True, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar {self.config_path}: {e}")

    def _load_task_states(self) -> Dict[str, Dict[str, Any]]:
        """Carga el historial de última ejecución de las tareas desde disco."""
        if SCHEDULER_STATE_FILE.exists():
            try:
                with open(SCHEDULER_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_task_states(self) -> None:
        """Guarda el historial de ejecuciones en disco."""
        try:
            SCHEDULER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULER_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.task_states, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def start(self) -> None:
        """Inicia el planificador y registra las tareas habilitadas."""
        if self._is_started:
            return

        self._register_all_jobs()
        self.scheduler.start()
        self._is_started = True
        logger.info("Motor planificador EcoGrid iniciado con éxito.")

    def stop(self) -> None:
        """Detiene el planificador limpiamente."""
        if self._is_started:
            self.scheduler.shutdown(wait=False)
            self._is_started = False
            logger.info("Motor planificador EcoGrid detenido.")

    def _register_all_jobs(self) -> None:
        """Registra los jobs en APScheduler según la configuración de tasks.yaml."""
        tasks = self.config.get("tasks", {})
        for task_id, task_cfg in tasks.items():
            if task_cfg.get("enabled", False):
                self._schedule_job(task_id, task_cfg)

    def _schedule_job(self, task_id: str, task_cfg: Dict[str, Any]) -> None:
        """Programa o reprograma un job en APScheduler."""
        # Eliminar job previo si existe
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)

        interval_minutes = int(task_cfg.get("interval_minutes", 60))
        if interval_minutes <= 0:
            interval_minutes = 60

        trigger = IntervalTrigger(minutes=interval_minutes, timezone=self.timezone)

        self.scheduler.add_job(
            func=self._job_wrapper,
            trigger=trigger,
            args=[task_id],
            id=task_id,
            name=task_cfg.get("name", task_id),
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        logger.info(f"Job programado: {task_id} cada {interval_minutes} minutos.")

    def _job_wrapper(self, task_id: str) -> None:
        """Envoltorio de ejecución segura que captura errores y actualiza métricas."""
        try:
            self.execute_task_now(task_id)
        except Exception as e:
            logger.error(f"Error inesperado en job {task_id}: {e}")

    def execute_task_now(self, task_id: str) -> Dict[str, Any]:
        """
        Ejecuta manualmente una tarea programada sin esperar al temporizador.
        Llama al conector adecuado, guarda el archivo en data/raw/ y registra el resultado.
        """
        tasks = self.config.get("tasks", {})
        if task_id not in tasks:
            raise ValueError(f"Tarea programada no encontrada: {task_id}")

        task_cfg = tasks[task_id]
        connector_id = task_cfg.get("connector")
        now = datetime.now(self.timezone)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Ejecutar mediante el servicio de ingesta existente
            result = self.ingestion_service.execute_source(connector_id)

            status_info = {
                "timestamp": now_str,
                "timestamp_iso": now.isoformat(),
                "status": "SUCCESS" if result.get("success") else "ERROR",
                "http_code": result.get("http_code", 0),
                "saved_file": result.get("saved_file"),
                "summary": result.get("summary", ""),
                "error": result.get("error")
            }

            self.task_states[task_id] = status_info
            self._save_task_states()

            return {
                "success": result.get("success", False),
                "task_id": task_id,
                "connector": connector_id,
                "status": status_info["status"],
                "http_code": status_info["http_code"],
                "saved_file": status_info["saved_file"],
                "summary": status_info["summary"],
                "error": status_info["error"],
                "timestamp": now_str
            }

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Fallo al ejecutar tarea {task_id}: {err_msg}")
            status_info = {
                "timestamp": now_str,
                "timestamp_iso": now.isoformat(),
                "status": "ERROR",
                "http_code": 0,
                "saved_file": None,
                "summary": f"Excepción durante la ejecución: {err_msg}",
                "error": err_msg
            }
            self.task_states[task_id] = status_info
            self._save_task_states()
            return {
                "success": False,
                "task_id": task_id,
                "connector": connector_id,
                "status": "ERROR",
                "http_code": 0,
                "saved_file": None,
                "summary": status_info["summary"],
                "error": err_msg,
                "timestamp": now_str
            }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Retorna la lista enriquecida de tareas con su estado, intervalos y tiempos."""
        tasks_list = []
        tasks = self.config.get("tasks", {})

        for task_id, task_cfg in tasks.items():
            job = self.scheduler.get_job(task_id) if self._is_started else None
            next_run = None
            next_run_iso = None

            if job and job.next_run_time:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                next_run_iso = job.next_run_time.isoformat()

            last_run = self.task_states.get(task_id)

            tasks_list.append({
                "id": task_id,
                "name": task_cfg.get("name", task_id),
                "connector": task_cfg.get("connector"),
                "description": task_cfg.get("description", ""),
                "enabled": bool(task_cfg.get("enabled", False)),
                "interval_minutes": int(task_cfg.get("interval_minutes", 60)),
                "cron": task_cfg.get("cron", ""),
                "destination_dir": task_cfg.get("destination_dir", "data/raw"),
                "params": task_cfg.get("params", {}),
                "next_run": next_run,
                "next_run_iso": next_run_iso,
                "last_run": last_run
            })

        return tasks_list

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una tarea específica por su ID."""
        all_tasks = self.get_tasks()
        for t in all_tasks:
            if t["id"] == task_id:
                return t
        return None

    def toggle_task(self, task_id: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Activa o desactiva dinámicamente una tarea programada."""
        tasks = self.config.get("tasks", {})
        if task_id not in tasks:
            raise ValueError(f"Tarea no encontrada: {task_id}")

        current_enabled = tasks[task_id].get("enabled", False)
        new_enabled = not current_enabled if enabled is None else bool(enabled)
        tasks[task_id]["enabled"] = new_enabled

        # Sincronizar con el scheduler
        if new_enabled:
            self._schedule_job(task_id, tasks[task_id])
        else:
            if self.scheduler.get_job(task_id):
                self.scheduler.remove_job(task_id)

        self._save_config()
        return self.get_task(task_id)

    def update_task_interval(self, task_id: str, interval_minutes: int) -> Dict[str, Any]:
        """Modifica la frecuencia de ejecución en minutos de una tarea."""
        if interval_minutes <= 0:
            raise ValueError("El intervalo debe ser un número entero mayor que 0.")

        tasks = self.config.get("tasks", {})
        if task_id not in tasks:
            raise ValueError(f"Tarea no encontrada: {task_id}")

        tasks[task_id]["interval_minutes"] = int(interval_minutes)
        tasks[task_id]["cron"] = f"*/{interval_minutes} * * * *" if interval_minutes < 60 else f"0 */{interval_minutes // 60} * * *"

        # Si está habilitada, reprogramar en el scheduler
        if tasks[task_id].get("enabled", False):
            self._schedule_job(task_id, tasks[task_id])

        self._save_config()
        return self.get_task(task_id)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Retorna el estado operativo general del motor planificador."""
        tasks = self.get_tasks()
        enabled_count = sum(1 for t in tasks if t["enabled"])
        return {
            "running": self._is_started and self.scheduler.running,
            "timezone": str(self.timezone),
            "total_tasks": len(tasks),
            "enabled_tasks": enabled_count,
            "jobs_in_scheduler": len(self.scheduler.get_jobs()) if self._is_started else 0
        }
