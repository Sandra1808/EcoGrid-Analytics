# EcoGrid-Analytics

Optimización de Costes Energéticos Mediante Predicción de Consumo.

## Integrantes del Equipo
* **Sandra González Guridi** - ML Engineer & MLOps / Front-End Lead
* **Ángel García-Page Rodríguez** - Team Leader, Integración y Arquitectura
* **Alexander Beltran Ferreres** -  Backend & Data Architect / Database Manager

## Objetivo del Proyecto
Desarrollar una aplicación web de analítica predictiva (SmartGrid-Predictor) basada en Machine Learning para series temporales que permita predecir el consumo eléctrico a 24 horas y traducirlo en un indicador de impacto económico, facilitando la toma de decisiones en comercializadoras energéticas y gestores de red.

## Tecnologías Previstas
* **Lenguajes:** Python 3.10+, HTML5, CSS3, JavaScript
* **Procesamiento de Datos & ML:** Pandas, NumPy, Scikit-Learn, XGBoost, Joblib
* **Entorno de Desarrollo y Cómputo:** Visual Studio Code & Google Colab
* **Backend & API:** Python (FastAPI / Uvicorn)
* **Base de Datos & ORM:** Oracle Database / Estructuras locales procesadas (`.csv`)
* **Visualización & Dashboard:** HTML5, CSS3, JavaScript (Chart.js)
* **Control de Versiones & MLOps:** Git, GitHub, Google Colab

## Arquitectura Resumida
El sistema sigue una arquitectura modular en capas:
1. **Capa de Ingesta y ETL (Python):** Captura y normaliza series temporales de REE, ESIOS y OMIE.
2. **Capa de Machine Learning (Python/Joblib):** Genera la predicción de demanda a 24 horas y evalúa métricas frente a un modelo baseline.
3. **Capa de Servicio Backend & API (Python / FastAPI):** Expone endpoints RESTful, gestiona la lógica de negocio e indicadores de impacto económico (€).
4. **Capa de Persistencia:** Almacenamiento estructurado de datasets maestros y modelos entrenados.
5. **Capa de Presentación (Frontend Web):** Interfaz responsive construida con HTML5, CSS3 y JavaScript (Chart.js) para la supervisión de curvas y alertas operativas.

## Cómo Ejecutar el Proyecto

Dado que el sistema se compone de un pipeline analítico en Python, un backend en Spring Boot y una interfaz web, la ejecución preliminar se divide en las siguientes fases:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Sandra1808/EcoGrid-Analytics.git
   cd EcoGrid-Analytics
   ```

2. **Configuración del entorno de datos y Machine Learning (Python):**
   * Se recomienda utilizar un entorno virtual para la ejecución de los scripts y dependencias:
   ```bash
   python -m venv venv
   ```

   En Windows PowerShell:

   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install -r environment/requirements.txt
   ```

   En macOS o Linux:

   ```bash
   source venv/bin/activate
   pip install -r environment/requirements.txt
   ```

3. **Ejecución de la API / Predicciones:**
   * Desde la raíz del proyecto, inicia FastAPI con Uvicorn. Ajusta la ruta del módulo si el archivo que declara `app` tiene otro nombre:

   ```bash
   uvicorn src.api.main:app --reload
   ```

4. **Visualización y Acceso al Frontend:**
   * Abre los componentes estáticos o la interfaz web desde la ruta `src/dashboard/` en tu navegador web o despliégala en un servidor local. El módulo `src/services/api.js` se comunica con la API en `http://localhost:8000/api`.

## Estructura del Repositorio
```text
EcoGrid-Analytics/
├── docs/                      # Documentación general y entregables 
│   └── NF0_Presentacion_alineacion_viabilidad.pdf
│   └── NF1_Documentación_Grupo4.pdf
│   └──arquitectura.png
│   └──modelo_relacional.png
├── data/                      # Datasets exportados y procesados
├── environment/               # Archivos de configuración de entorno (requirements.txt, etc.)
├── src/                       # Código fuente de la aplicación
│   ├── data/                    # Notebooks de Google Colab para ingesta y limpieza de datos
│   ├── models/                  # Modelos entrenados y artefactos (.joblib)
│   ├── api/                     # Backend y servicios API
│   ├──dashboard/                # Interfaz de usuario en HTML, CSS y JavaScript
    └──services/                 # Lógica de servicios y scripts auxiliares
├── .gitignore                   # Archivos ignorados por Git
└── README.md                    # Descripción general del proyecto




