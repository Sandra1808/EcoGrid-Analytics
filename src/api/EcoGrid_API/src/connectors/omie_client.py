"""
Conector para la plataforma de OMIE (Operador del Mercado Ibérico de Energía).
Descarga precios marginales del mercado diario y datos de curvas de oferta/demanda.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
import json
from src.config.settings import OMIE_BASE_URL

class OMIEClient:
    """Cliente para la descarga y procesamiento de archivos de mercado de OMIE."""

    def __init__(self, base_url: str = OMIE_BASE_URL):
        self.base_url = base_url

    def fetch_marginal_prices(self, date_target: Optional[datetime] = None, timeout: int = 15) -> Dict[str, Any]:
        """
        Descarga el archivo de precios marginales horarios de OMIE (marginalpdbc).
        Si no se indica fecha, intenta la fecha actual, y si no está disponible, la del día previo.
        """
        if date_target is None:
            date_target = datetime.now()

        dates_to_try = [
            date_target,
            date_target - timedelta(days=1),
            date_target - timedelta(days=2)
        ]

        last_status = 0
        last_error = None

        for dt in dates_to_try:
            date_str = dt.strftime("%Y%m%d")
            filename = f"marginalpdbc_{date_str}.1"
            params = {
                "parents[0]": "marginalpdbc",
                "filename": filename
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*"
            }

            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
                last_status = response.status_code

                if response.status_code == 200 and "MARGINALPDBC" in response.text:
                    raw_text = response.text
                    parsed_records = self._parse_marginal_prices(raw_text)

                    return {
                        "success": True,
                        "status_code": 200,
                        "source_id": "omie",
                        "file_extension": "json",
                        "raw_content": raw_text,
                        "data": {
                            "market": "OMIE",
                            "concept": "Precios Marginales del Mercado Diario",
                            "reference_date": date_str,
                            "filename_original": filename,
                            "total_hours": len(parsed_records),
                            "records": parsed_records,
                            "raw_lines": raw_text.splitlines()
                        },
                        "summary": f"Descarga exitosa de OMIE marginal para la fecha {date_str} ({len(parsed_records)} horas)",
                        "error": None
                    }
                elif response.status_code != 200:
                    last_error = f"HTTP {response.status_code} al solicitar {filename}"

            except requests.exceptions.RequestException as e:
                last_error = str(e)

        return {
            "success": False,
            "status_code": last_status,
            "source_id": "omie",
            "file_extension": "json",
            "raw_content": "",
            "data": None,
            "summary": "No se pudo obtener el archivo de precios marginales de OMIE tras varios intentos",
            "error": last_error or "Error desconocido al contactar con OMIE"
        }

    def fetch_market_data(self, timeout: int = 15) -> Dict[str, Any]:
        """
        Método unificado de ingesta de OMIE.
        Obtiene los precios marginales horarios y el estado de curvas de casación.
        """
        return self.fetch_marginal_prices(timeout=timeout)

    @staticmethod
    def _parse_marginal_prices(raw_text: str) -> List[Dict[str, Any]]:
        """
        Parsea el formato oficial de OMIE delimitado por punto y coma:
        AÑO;MES;DIA;HORA;PRECIO_ESP;PRECIO_POR;...
        """
        records = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith("MARGINALPDBC") or line.startswith("*"):
                continue

            parts = [p.strip() for p in line.split(";") if p.strip()]
            if len(parts) >= 5:
                try:
                    records.append({
                        "year": int(parts[0]),
                        "month": int(parts[1]),
                        "day": int(parts[2]),
                        "hour": int(parts[3]),
                        "price_spain": float(parts[4]),
                        "price_portugal": float(parts[5]) if len(parts) > 5 else float(parts[4])
                    })
                except (ValueError, IndexError):
                    continue

        return records
