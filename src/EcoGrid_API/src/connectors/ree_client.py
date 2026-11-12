"""
Conector para la API de Red Eléctrica de España (REE / ESIOS).
Gestiona la demanda real e indicativa (programada / prevista).
Utiliza el token ESIOS si está disponible en .env, con soporte para la API pública de REE.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
import json
from src.config.settings import (
    ESIOS_BASE_URL,
    REE_APIDATOS_BASE_URL,
    ESIOS_API_TOKEN
)

class REEClient:
    """Cliente para las APIs de Red Eléctrica de España (ESIOS y REE Apidatos)."""

    def __init__(self, token: Optional[str] = None):
        self.token = (token or ESIOS_API_TOKEN).strip()
        self.esios_base_url = ESIOS_BASE_URL
        self.apidatos_base_url = REE_APIDATOS_BASE_URL

    @property
    def has_valid_token(self) -> bool:
        """Comprueba si existe un token configurado que no sea el texto por defecto."""
        return bool(self.token and self.token != "tu_token_aqui")

    def fetch_demand(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Obtiene datos de demanda eléctrica (real, prevista y programada).
        Si existe un token de ESIOS, consulta directamente a api.esios.ree.es.
        Si no existe token, consulta la API abierta apidatos.ree.es indicando la necesidad de token ESIOS.
        """
        now = datetime.now()
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=1)

        # Si el token de ESIOS está configurado, consultar la API oficial de ESIOS
        if self.has_valid_token:
            return self._fetch_from_esios(start_date, end_date, timeout)
        else:
            # Si no hay token, usar el endpoint público oficial de REE (Apidatos)
            return self._fetch_from_apidatos(start_date, end_date, timeout)

    def _fetch_from_esios(self, start_date: datetime, end_date: datetime, timeout: int) -> Dict[str, Any]:
        """Consulta directa a la API e-sios con autenticación por Token."""
        start_str = start_date.strftime("%Y-%m-%dT00:00")
        end_str = end_date.strftime("%Y-%m-%dT23:59")

        # Indicador 1293: Demanda real peninsular en tiempo real
        # Indicador 460: Previsión diaria de la demanda
        url_real = f"{self.esios_base_url}/indicators/1293"
        headers = {
            "Accept": "application/json; application/vnd.esios-api-v2+json",
            "Content-Type": "application/json",
            "Authorization": f'Token token="{self.token}"',
            "User-Agent": "EcoGrid-Analytics/1.0"
        }
        params = {
            "start_date": start_str,
            "end_date": end_str
        }

        try:
            response = requests.get(url_real, headers=headers, params=params, timeout=timeout)
            status_code = response.status_code
            raw_text = response.text

            if status_code == 200:
                parsed_data = response.json()
                values_count = len(parsed_data.get("indicator", {}).get("values", []))
                return {
                    "success": True,
                    "status_code": status_code,
                    "source_id": "ree_esios",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": {
                        "api_origin": "api.esios.ree.es",
                        "indicator_id": 1293,
                        "indicator_name": "Demanda Real",
                        "authenticated": True,
                        "payload": parsed_data
                    },
                    "summary": f"Descarga exitosa desde ESIOS API (Indicador 1293: {values_count} registros)",
                    "error": None
                }
            elif status_code == 401:
                return {
                    "success": False,
                    "status_code": 401,
                    "source_id": "ree_esios",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": None,
                    "summary": "Token de ESIOS no autorizado o inválido (HTTP 401)",
                    "error": "El token configurado en .env no fue aceptado por api.esios.ree.es. Solicita uno en consultasios@ree.es (ver acciones.md)."
                }
            else:
                return {
                    "success": False,
                    "status_code": status_code,
                    "source_id": "ree_esios",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": None,
                    "summary": f"Error devuelto por ESIOS: HTTP {status_code}",
                    "error": raw_text[:300]
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status_code": 0,
                "source_id": "ree_esios",
                "file_extension": "json",
                "raw_content": "",
                "data": None,
                "summary": "Error de conexión con ESIOS REE",
                "error": str(e)
            }

    def _fetch_from_apidatos(self, start_date: datetime, end_date: datetime, timeout: int) -> Dict[str, Any]:
        """
        Consulta a la API pública abierta de REE (apidatos.ree.es).
        Proporciona demanda en tiempo real, prevista y programada de forma funcional y gratuita.
        """
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        url = f"{self.apidatos_base_url}?start_date={start_str}T00:00&end_date={end_str}T23:59&time_trunc=hour"
        headers = {
            "Accept": "application/json",
            "User-Agent": "EcoGrid-Analytics/1.0"
        }

        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            status_code = response.status_code
            raw_text = response.text

            if status_code == 200:
                parsed = response.json()
                series = [item.get("type", "Serie") for item in parsed.get("included", [])]
                return {
                    "success": True,
                    "status_code": 200,
                    "source_id": "ree_esios",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": {
                        "api_origin": "apidatos.ree.es (Open Data REE)",
                        "notice": "Token ESIOS no detectado en .env. Conexión establecida mediante API pública de REE. Para conexión ESIOS V2 oficial, complete ESIOS_API_TOKEN según acciones.md.",
                        "has_esios_token": False,
                        "series_disponibles": series,
                        "payload": parsed
                    },
                    "summary": f"Descarga exitosa desde REE Apidatos ({', '.join(series) if series else 'Demanda real/prevista'})",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "status_code": status_code,
                    "source_id": "ree_esios",
                    "file_extension": "json",
                    "raw_content": raw_text,
                    "data": None,
                    "summary": f"Error de respuesta en API REE: HTTP {status_code}",
                    "error": raw_text[:300]
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status_code": 0,
                "source_id": "ree_esios",
                "file_extension": "json",
                "raw_content": "",
                "data": None,
                "summary": "Error de conexión con API REE Apidatos",
                "error": str(e)
            }
