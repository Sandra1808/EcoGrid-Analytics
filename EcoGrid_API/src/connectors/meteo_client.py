"""
Conector para la API de Open-Meteo.
Obtiene datos meteorológicos horarios para Madrid con variables eólicas, térmicas y de radiación.
"""

from typing import Dict, Any, Optional
import requests
import json
from src.config.settings import (
    OPEN_METEO_BASE_URL,
    OPEN_METEO_MADRID_LAT,
    OPEN_METEO_MADRID_LON,
    OPEN_METEO_TIMEZONE
)

class OpenMeteoClient:
    """Cliente HTTP para interactuar con la API pública de Open-Meteo."""

    HOURLY_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_speed_80m",
        "wind_speed_120m",
        "wind_speed_180m",
        "wind_direction_10m",
        "wind_direction_80m",
        "wind_direction_120m",
        "wind_direction_180m",
        "cloud_cover",
        "direct_normal_irradiance",
        "global_tilted_irradiance",
        "shortwave_radiation"
    ]

    def __init__(self, base_url: str = OPEN_METEO_BASE_URL):
        self.base_url = base_url

    def fetch_madrid_weather(
        self,
        latitude: float = OPEN_METEO_MADRID_LAT,
        longitude: float = OPEN_METEO_MADRID_LON,
        timezone: str = OPEN_METEO_TIMEZONE,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Realiza la petición a Open-Meteo para las coordenadas de Madrid.
        Retorna un diccionario con estado, contenido en bruto y metadatos.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": self.HOURLY_VARIABLES,
            "timezone": timezone
        }

        headers = {
            "User-Agent": "EcoGrid-Analytics/1.0 (DataIngestionBot)"
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            status_code = response.status_code
            raw_text = response.text

            if response.status_code == 200:
                parsed_json = response.json()
                hours_count = len(parsed_json.get("hourly", {}).get("time", []))
                return {
                    "success": True,
                    "status_code": status_code,
                    "source_id": "open_meteo",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": parsed_json,
                    "summary": f"Descarga exitosa de {hours_count} registros horarios para Madrid ({latitude}, {longitude})",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "status_code": status_code,
                    "source_id": "open_meteo",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": None,
                    "summary": f"Respuesta inesperada de Open-Meteo: HTTP {status_code}",
                    "error": response.text[:300]
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status_code": 0,
                "source_id": "open_meteo",
                "file_extension": "json",
                "raw_content": "",
                "data": None,
                "summary": "Error de conexión al conectar con Open-Meteo",
                "error": str(e)
            }
