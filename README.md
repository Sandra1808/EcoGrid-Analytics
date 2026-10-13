# EcoGrid-Analytics

Optimización de Costes Energéticos Mediante Predicción de Consumo.

## Integrantes del Equipo
* **Sandra González Guridi** - ML Engineer & MLOps / Front-End Lead
* **Ángel García-Page Rodríguez** - Team Leader, Integración y Arquitectura
* **Alexander Beltran Ferreres** -  Backend & Data Architect / Database Manager

## Objetivo del Proyecto
Desarrollar una aplicación web de analítica predictiva (SmartGrid-Predictor) basada en Machine Learning para series temporales que permita predecir el consumo eléctrico a 24 horas y traducirlo en un indicador de impacto económico, facilitando la toma de decisiones en comercializadoras energéticas y gestores de red.

## Tecnologías Previstas
* **Lenguajes:** Python 3.10+, Java, HTML5, CSS3, JavaScript, PHP
* **Procesamiento de Datos & ML:** Pandas, NumPy, Scikit-Learn, XGBoost, Prophet, Joblib
* **Entorno de Desarrollo y Cómputo:** Visual Studio Code & Google Colab
* **Backend & API:** Java con Spring Boot
* **Base de Datos & ORM:** Oracle Database
* **Visualización & Dashboard:** HTML5, CSS3, JavaScript (Chart.js), PHP
* **Control de Versiones & MLOps:** Git, GitHub, Git LFS, Google Colab

## Arquitectura Resumida
El sistema sigue una arquitectura modular en capas (N-Tiers):
1. **Capa de Ingesta y ETL (Python):** Captura y normaliza series temporales de REE, ESIOS y OMIE.
2. **Capa de Machine Learning (Python/Joblib):** Genera la predicción de demanda a 24 horas y evalúa métricas frente a un modelo baseline.
3. **Capa de Servicio Backend (Spring Boot 3 / Java 17):** Expone endpoints RESTful, gestiona la seguridad, lógica de negocio e indicadores de impacto económico (€) y la multitenancy basada en organización por CIF.
4. **Capa de Persistencia (Oracle Database):** Almacena el modelo relacional corporativo (con tablas para gestión de usuarios/roles por CIF, dimensiones temporales, histórico de consumo, predicciones, meteorología y alertas).
5. **Capa de Presentación (Frontend Web):** Interfaz responsive construida con HTML5, CSS3 y JavaScript (Chart.js) para la supervisión de curvas y alertas operativas.

## Cómo Ejecutar el Proyecto

Dado que el sistema se compone de un pipeline analítico en Python, un backend en Spring Boot y una interfaz web, la ejecución preliminar se divide en las siguientes fases:

1. **Clonar el repositorio:**
   git clone [https://github.com/Sandra1808/EcoGrid-Analytics.git](https://github.com/Sandra1808/EcoGrid-Analytics.git)
   cd EcoGrid-Analytics

2. **Configuración del entorno de datos y Machine Learning (Python):**
   Se recomienda utilizar un entorno virtual para la ejecución de los scripts de ingesta y modelado:
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r environment/requirements.txt

3. **Configuración y ejecución del Backend (Spring Boot):**
   * Abre la carpeta contenedora del backend (`src/backend/`) en tu IDE.
   * Configura los parámetros de conexión a tu base de datos Oracle en el fichero de propiedades (`src/main/resources/application.properties`):
     spring.datasource.url=jdbc:oracle:thin:@//localhost:1521/ORCL
     spring.datasource.username=tu_usuario
     spring.datasource.password=tu_contraseña
   * Ejecuta la aplicación mediante Maven:
     mvn spring-boot:run

4. **Visualización y Acceso al Frontend:**
   * Abre los componentes estáticos o la interfaz web desde la ruta `src/frontend/` en tu navegador web o despliégala en un servidor local para verificar la integración con los endpoints RESTful.

## Estructura del Repositorio
```text
EcoGrid-Analytics/
├── docs/                      # Documentación general y entregables del curso (PDFs, NF1...)
│   └── NF0_Presentacion_alineacion_viabilidad.pdf
│   └── NF1_Documentación_Grupo4.pdf
│   └──arquitectura.png
│   └──modelo_relacional.png
├── src/                       # Código fuente de la aplicación
│   ├── data/                  # Notebooks de Google Colab para ingesta y limpieza de datos
│   ├── models/                # Notebooks de Google Colab para entrenamiento y evaluación
│   ├── api/                   # Servidor backend y endpoints en Spring Boot
│   └── dashboard/             # Interfaz de usuario en HTML, CSS y JavaScript
├── data/                      # Datasets (archivos .csv / .parquet localmente)
├── environment/               # Archivos de configuración de entorno (requirements.txt / environment.yml)
├── .gitignore                 # Archivos ignorados por Git
└── README.md                  # Descripción general del proyecto




