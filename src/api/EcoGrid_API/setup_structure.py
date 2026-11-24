import os

# Definición de la estructura de directorios y archivos base
FOLDER_STRUCTURE = [
    "data/raw",
    "src/connectors",
    "src/services",
    "src/config",
    "src/static",
    "src/templates"
]

FILES = {
    # Archivos de configuración y documentación raíz
    "requirements.txt": """fastapi>=0.100.0
uvicorn>=0.22.0
requests>=2.31.0
pandas>=2.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
jinja2>=3.1.2
""",
    ".env.example": """HOST=127.0.0.1
PORT=8000
DATA_DIR=data/raw
LOG_LEVEL=INFO

ORACLE_ENABLED=false
ORACLE_USER=
ORACLE_PASSWORD=
ORACLE_DSN=
ORACLE_WALLET_DIR=
ORACLE_WALLET_PASSWORD=
ORACLE_CONNECT_TIMEOUT=20

CALENDAR_TZ=Europe/Madrid
NACIONAL_CCAA_CODINE=00
METEO_CCAA_CODINE=13

ESIOS_API_TOKEN=
SPRING_API_BASE_URL=http://127.0.0.1:8080
SPRING_PREDICTIONS_API_KEY=
PREDICTION_MODEL_ID=1
PREDICTION_MODEL_PATH=models/modelo_xgboost_demanda.json
""",
    "README.md": """# EcoGrid API

Ejecuta `uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload` desde esta carpeta después de copiar `.env.example` a `.env`. Nunca introduzcas credenciales reales en `.env.example`.
""",
}

def create_project_structure():
    print("🚀 Creando estructura del proyecto EcoGrid_API...")
    
    # Crear directorios
    for folder in FOLDER_STRUCTURE:
        os.makedirs(folder, exist_ok=True)
        print(f"  [+] Directorio: {folder}")
        
    # Crear archivos
    for file_path, content in FILES.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  [+] Archivo: {file_path}")
        else:
            print(f"  [=] El archivo ya existe (omitido): {file_path}")

    print("\n✅ Estructura del proyecto creada con éxito.")

if __name__ == "__main__":
    create_project_structure()