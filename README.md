# EcoGrid-Analytics

Optimización de Costes Energéticos Mediante Predicción de Consumo.

## Integrantes del Equipo
* **Sandra González Guridi** - Data Engineer & MLOps / Backend
* **Ángel García-Page Rodríguez** - ML Engineer & BI / Front-End Analyst

## Objetivo del Proyecto
Desarrollar un pipeline de datos y un modelo de Machine Learning supervisado para series temporales que permita predecir el consumo eléctrico (horario/diario) y anticipar picos de demanda. El sistema se enriquece con variables meteorológicas, calendarios laborales/festivos y tramos tarifarios para facilitar la toma de decisiones en comercializadoras y gestores de red.

## Tecnologías Previstas
* **Lenguaje:** Python 3.10+
* **Procesamiento de Datos:** Pandas, NumPy
* **Machine Learning:** Scikit-Learn, XGBoost / LightGBM
* **Backend & API:** FastAPI, Uvicorn
* **Visualización & Dashboard:** Streamlit / Power BI
* **Control de Versiones:** Git & GitHub

## Estructura del Repositorio
```text
SmartGrid-Predictor/
├── docs/               # Documentación general y entregables del curso (PDFs, NF1...)
│   └── NF1_Presentacion_y_Viabilidad.pdf
├── src/                # Código fuente de la aplicación
│   ├── data/           # Scripts de ingesta, limpieza y preprocesamiento
│   ├── models/         # Entrenamiento, evaluación y serialización de modelos
│   ├── api/            # Servidor backend y endpoints en FastAPI
│   └── dashboard/      # Interfaz de usuario y visualización en Streamlit
├── data/               # Datasets (archivos .csv / .parquet localmente)
├── environment/        # Archivos de configuración de entorno (requirements.txt / environment.yml)
├── .gitignore          # Archivos ignorados por Git
└── README.md           # Descripción general del proyecto
