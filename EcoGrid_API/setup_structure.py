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
    ".env": """# Archivo de variables de entorno locales
PORT=8000
HOST=127.0.0.1
DATA_DIR=data/raw

# Claves de APIs Externas (Completar según acciones.md)
ESIOS_API_TOKEN=
""",
    ".env.example": """# Plantilla de variables de entorno
PORT=8000
HOST=127.0.0.1
DATA_DIR=data/raw

# Claves de APIs Externas
ESIOS_API_TOKEN=tu_token_aqui
""",
    "acciones.md": """# ACCIONES EXTERNAS E INTERNAS REQUERIDAS

## 🚨 ACCIONES EXTERNAS (CLAVES Y REGISTROS)
1. **ESIOS / REE (Red Eléctrica de España)**:
   - Es necesario solicitar un API Token enviando un correo a `consultasios@ree.es` indicando el uso para investigación/proyecto.
   - Una vez recibido, añadir el token en el archivo `.env` en la variable `ESIOS_API_TOKEN`.

2. **Open-Meteo**:
   - No requiere API Key para uso estándar no comercial.

3. **OMIE**:
   - Se utiliza la descarga pública o peticiones directas. Si en el futuro se requiere autenticación, documentar aquí.

---

## 🛠️ ACCIONES INTERNAS (CONFIGURACIÓN DE ENTORNO)
1. Ejecutar el entorno virtual (`venv`).
2. Instalar dependencias: `pip install -r requirements.txt`.
3. Iniciar el servidor local: `uvicorn src.main:app --reload`.
""",
    "README.md": "# EcoGrid API - Gestor de Ingesta y Conexiones API\n\nAplicación local para la gestión, llamada y recepción de datos desde orígenes heterogéneos (Open-Meteo, OMIE, REE/ESIOS).",
    
    # Archivos de código python iniciales
    "src/__init__.py": "",
    "src/config/__init__.py": "",
    "src/config/settings.py": "# Configuración global de la aplicación\n",
    "src/connectors/__init__.py": "",
    "src/connectors/meteo_client.py": "# Conector Open-Meteo\n",
    "src/connectors/omie_client.py": "# Conector OMIE\n",
    "src/connectors/ree_client.py": "# Conector REE / ESIOS\n",
    "src/services/__init__.py": "",
    "src/services/ingestion_service.py": "# Servicio de orquestación de ingesta\n",
    "src/main.py": "# Punto de entrada principal FastAPI\n",

    # Archivos HTML/JS básicos para la interfaz de administración
    "src/templates/index.html": "<!-- Panel de administración web de EcoGrid API -->\n",
    "src/static/app.js": "// Lógica de interacción web para activar/desactivar orígenes y disparar llamadas\n",
    "src/static/style.css": "/* Estilos del panel de administración */\n"
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