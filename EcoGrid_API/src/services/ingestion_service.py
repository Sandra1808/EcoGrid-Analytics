"""
Servicio de orquestación de ingesta de datos y gestión de archivos brutos.
Coordina llamadas a conectores, control de estado de fuentes y guardado en data/raw/.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import os

from src.config.settings import DATA_RAW_DIR, ESIOS_API_TOKEN
from src.connectors.meteo_client import OpenMeteoClient
from src.connectors.omie_client import OMIEClient
from src.connectors.ree_client import REEClient

STATE_FILE = DATA_RAW_DIR.parent / "sources_state.json"

class IngestionService:
    """Servicio principal de ingesta y administración de orígenes."""

    def __init__(self, raw_dir: Path = DATA_RAW_DIR):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.sources: Dict[str, Dict[str, Any]] = self._init_sources_catalog()
        self._load_saved_state()

    def _init_sources_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Inicializa el catálogo base de orígenes de datos disponibles."""
        has_esios = bool(ESIOS_API_TOKEN and ESIOS_API_TOKEN != "tu_token_aqui")
        return {
            "open_meteo": {
                "id": "open_meteo",
                "name": "Open-Meteo Weather",
                "category": "Meteorología & Viento",
                "description": "Datos horarios de Madrid: temperatura, humedad, viento multinivel (10m, 80m, 120m, 180m), nubosidad y radiación solar.",
                "active": True,
                "endpoint": "https://api.open-meteo.com/v1/forecast",
                "auth_type": "Pública (Sin API Key)",
                "requires_token": False,
                "token_configured": True,
                "last_run": None
            },
            "omie": {
                "id": "omie",
                "name": "OMIE Mercado Diario",
                "category": "Mercado Eléctrico Ibérico",
                "description": "Precios marginales horarios (€/MWh) y curvas de oferta/demanda del mercado diario (España y Portugal).",
                "active": True,
                "endpoint": "https://www.omie.es/es/file-download",
                "auth_type": "Pública / Descarga directa",
                "requires_token": False,
                "token_configured": True,
                "last_run": None
            },
            "ree_esios": {
                "id": "ree_esios",
                "name": "REE / ESIOS Demanda",
                "category": "Operador del Sistema Eléctrico",
                "description": "Demanda eléctrica peninsular en tiempo real, prevista y programada de Red Eléctrica de España.",
                "active": True,
                "endpoint": "https://api.esios.ree.es (o Fallback Público REE)",
                "auth_type": "Token ESIOS (consultasios@ree.es)",
                "requires_token": True,
                "token_configured": has_esios,
                "last_run": None
            }
        }

    def _save_state(self) -> None:
        """Guarda el estado actual de las fuentes en disco."""
        try:
            state_data = {
                src_id: {
                    "active": src["active"],
                    "last_run": src["last_run"]
                }
                for src_id, src in self.sources.items()
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_saved_state(self) -> None:
        """Carga el estado persistido si existe."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for src_id, state in saved.items():
                        if src_id in self.sources:
                            self.sources[src_id]["active"] = state.get("active", True)
                            self.sources[src_id]["last_run"] = state.get("last_run", None)
            except Exception:
                pass

    def get_sources(self) -> List[Dict[str, Any]]:
        """Retorna la lista de todas las fuentes con su estado."""
        # Refrescar estado de token por si cambió el .env
        has_esios = bool(ESIOS_API_TOKEN and ESIOS_API_TOKEN != "tu_token_aqui")
        self.sources["ree_esios"]["token_configured"] = has_esios
        return list(self.sources.values())

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una fuente por su ID."""
        return self.sources.get(source_id)

    def toggle_source(self, source_id: str, active: Optional[bool] = None) -> Dict[str, Any]:
        """Activa o desactiva un origen de datos."""
        if source_id not in self.sources:
            raise ValueError(f"Origen desconocido: {source_id}")

        if active is None:
            self.sources[source_id]["active"] = not self.sources[source_id]["active"]
        else:
            self.sources[source_id]["active"] = bool(active)

        self._save_state()
        return self.sources[source_id]

    def execute_source(self, source_id: str) -> Dict[str, Any]:
        """
        Dispara la ejecución manual de un origen de datos y guarda el resultado en data/raw/.
        """
        if source_id not in self.sources:
            raise ValueError(f"Origen desconocido: {source_id}")

        execution_ts = datetime.now()
        ts_filename = execution_ts.strftime("%Y%m%d_%H%M%S")
        ts_iso = execution_ts.isoformat()

        # Llamar al conector adecuado
        if source_id == "open_meteo":
            client = OpenMeteoClient()
            result = client.fetch_madrid_weather()
        elif source_id == "omie":
            client = OMIEClient()
            result = client.fetch_market_data()
        elif source_id == "ree_esios":
            client = REEClient()
            result = client.fetch_demand()
        else:
            raise ValueError(f"No hay conector registrado para: {source_id}")

        saved_filename = None
        file_size_bytes = 0

        if result.get("success"):
            ext = result.get("file_extension", "json")
            saved_filename = f"{source_id}_{ts_filename}.{ext}"
            file_path = self.raw_dir / saved_filename

            # Guardar el contenido devuelto respetando formato
            raw_data = result.get("data")
            raw_content = result.get("raw_content")

            try:
                if ext == "json" and raw_data is not None:
                    # Guardar JSON con formato legible
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(raw_data, f, indent=2, ensure_ascii=False)
                elif raw_content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(raw_content)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump({"raw_response": result}, f, indent=2)

                file_size_bytes = file_path.stat().st_size
            except Exception as e:
                result["success"] = False
                result["error"] = f"Error al guardar archivo en disco: {e}"
                saved_filename = None

        # Registrar estado de la última ejecución
        status_label = "SUCCESS" if result.get("success") else "ERROR"
        last_run_info = {
            "status": status_label,
            "http_code": result.get("status_code", 0),
            "timestamp": ts_iso,
            "timestamp_formatted": execution_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "saved_file": saved_filename,
            "file_size": file_size_bytes,
            "summary": result.get("summary", ""),
            "error": result.get("error")
        }

        self.sources[source_id]["last_run"] = last_run_info
        self._save_state()

        return {
            "source_id": source_id,
            "source_name": self.sources[source_id]["name"],
            "success": result.get("success"),
            "http_code": result.get("status_code"),
            "timestamp": ts_iso,
            "saved_file": saved_filename,
            "file_size": file_size_bytes,
            "summary": result.get("summary"),
            "error": result.get("error")
        }

    def execute_active_sources(self) -> List[Dict[str, Any]]:
        """
        Ejecuta la ingesta de todas las fuentes que estén marcadas como activas.
        """
        results = []
        for src_id, src in self.sources.items():
            if src.get("active", False):
                res = self.execute_source(src_id)
                results.append(res)
        return results

    def list_raw_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos los archivos guardados en data/raw/ ordenados por fecha descendente.
        """
        files = []
        if not self.raw_dir.exists():
            return files

        for p in self.raw_dir.iterdir():
            if p.is_file():
                stat = p.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                
                # Identificar el origen a partir del prefijo
                name = p.name
                source_id = "desconocido"
                for s_id in self.sources.keys():
                    if name.startswith(s_id):
                        source_id = s_id
                        break

                files.append({
                    "filename": name,
                    "source_id": source_id,
                    "source_name": self.sources.get(source_id, {}).get("name", "Desconocido"),
                    "size_bytes": stat.st_size,
                    "size_formatted": self._format_size(stat.st_size),
                    "created_at": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": mod_time.isoformat(),
                    "extension": p.suffix.lstrip(".")
                })

        # Ordenar por fecha descendente
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return files

    def get_raw_file_content(self, filename: str) -> Dict[str, Any]:
        """
        Lee el contenido de un archivo en data/raw/ de forma segura.
        """
        # Validación de seguridad: evitar path traversal
        safe_name = Path(filename).name
        file_path = self.raw_dir / safe_name

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Archivo no encontrado: {safe_name}")

        stat = file_path.stat()
        content_text = file_path.read_text(encoding="utf-8", errors="replace")
        
        is_json = False
        parsed_json = None
        if file_path.suffix.lower() == ".json":
            try:
                parsed_json = json.loads(content_text)
                is_json = True
            except Exception:
                pass

        return {
            "filename": safe_name,
            "size_bytes": stat.st_size,
            "size_formatted": self._format_size(stat.st_size),
            "is_json": is_json,
            "content": parsed_json if is_json else content_text,
            "raw_text": content_text,
            "lines_count": len(content_text.splitlines())
        }

    def delete_raw_file(self, filename: str) -> bool:
        """Elimina un archivo de data/raw/ de forma segura."""
        safe_name = Path(filename).name
        file_path = self.raw_dir / safe_name

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        return False

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Convierte bytes a formato legible (KB, MB)."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
