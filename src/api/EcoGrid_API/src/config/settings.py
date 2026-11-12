"""
Configuración global de la aplicación EcoGrid Analytics.
Carga variables de entorno y define rutas seguras dentro del proyecto.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Rutas base estrictamente relativas a la raíz del proyecto EcoGrid_API
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

# Cargar variables de entorno si el archivo .env existe
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

# Configuración del servidor
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Directorio de almacenamiento de datos en bruto
DATA_RAW_DIR = BASE_DIR / os.getenv("DATA_DIR", "data/raw")
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

# Tokens y credenciales de APIs externas
ESIOS_API_TOKEN = os.getenv("ESIOS_API_TOKEN", "").strip()

# Parámetros por defecto para Open-Meteo (Madrid)
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MADRID_LAT = 40.41
OPEN_METEO_MADRID_LON = -3.73
OPEN_METEO_TIMEZONE = "Europe/Madrid"

# Parámetros por defecto para OMIE
OMIE_BASE_URL = "https://www.omie.es/es/file-download"

# Parámetros por defecto para REE / ESIOS
ESIOS_BASE_URL = "https://api.esios.ree.es"
REE_APIDATOS_BASE_URL = "https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real"
