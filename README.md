# EcoGrid-Analytics

Optimización de Costes Energéticos Mediante Predicción de Consumo.

## Integrantes del Equipo
* **Sandra González Guridi** - ML Engineer & MLOps / Front-End Lead
* **Ángel García-Page Rodríguez** - Backend & Data Architect / Database Manager

## Objetivo del Proyecto
Desarrollar una aplicación web de analítica predictiva (SmartGrid-Predictor) basada en Machine Learning para series temporales que permita predecir el consumo eléctrico a 24 horas y traducirlo en un indicador de impacto económico, facilitando la toma de decisiones en comercializadoras energéticas y gestores de red.

## Tecnologías Previstas
* **Lenguajes:** Python 3.10+, Java, HTML5, CSS3, JavaScript
* **Procesamiento de Datos & ML:** Pandas, NumPy, Scikit-Learn, XGBoost, Prophet, Joblib
* **Entorno de Desarrollo y Cómputo:** Visual Studio Code & Google Colab
* **Backend & API:** Java con Spring Boot
* **Base de Datos & ORM:** Oracle Database
* **Visualización & Dashboard:** HTML5, CSS3, JavaScript (Chart.js)
* **Control de Versiones & MLOps:** Git, GitHub, Git LFS

## Estructura del Repositorio
```text
EcoGrid-Analytics/
├── docs/                      # Documentación general y entregables del curso (PDFs, NF1...)
│   └── NF1_Presentacion_alineacion_viabilidad.pdf
├── src/                       # Código fuente de la aplicación
│   ├── data/                  # Notebooks de Google Colab para ingesta y limpieza de datos
│   ├── models/                # Notebooks de Google Colab para entrenamiento y evaluación
│   ├── api/                   # Servidor backend y endpoints en Spring Boot
│   └── dashboard/             # Interfaz de usuario en HTML, CSS y JavaScript
├── data/                      # Datasets (archivos .csv / .parquet localmente)
├── environment/               # Archivos de configuración de entorno (requirements.txt / environment.yml)
├── .gitignore                 # Archivos ignorados por Git
└── README.md                  # Descripción general del proyecto