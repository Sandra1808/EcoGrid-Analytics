# 📋 GUÍA DE ACCIONES EXTERNAS E INTERNAS - ECOGRID ANALYTICS

Este documento detalla todas las configuraciones, registros externos, claves de API y pasos operativos necesarios para el funcionamiento de la plataforma de ingesta de datos de EcoGrid.

---

## 🚨 1. ACCIONES EXTERNAS (REGISTROS Y CREDENCIALES)

### A. Red Eléctrica de España (ESIOS / REE)
> [!IMPORTANT]
> **ESTADO ACTUAL**:
> Mientras no se configure un token personal de ESIOS, el conector `ree_client.py` utiliza de manera automática el endpoint público oficial de Red Eléctrica (`apidatos.ree.es`) para consultar la demanda en tiempo real, prevista y programada.
>
> Para desbloquear acceso directo a la API oficial e-sios V2 (`api.esios.ree.es`) con granularidad de 5 minutos e indicadores especializados (1293 para demanda real peninsular, 460 para previsión y 545 para programada):
> 1. Redactar y enviar un correo electrónico a: **`consultasios@ree.es`**
> 2. Asunto: *Solicitud de Token Personal API e-sios - EcoGrid Analytics*
> 3. Cuerpo del mensaje:
>    ```text
>    Estimado equipo de soporte de e-sios (REE),
>    
>    Me pongo en contacto con ustedes para solicitar un token de acceso personal a la API de e·sios 
>    (api.esios.ree.es) para el desarrollo e investigación del proyecto EcoGrid Analytics enfocado 
>    en análisis de demanda y eficiencia en la red eléctrica peninsular.
>    
>    Nombre del solicitante: [Tu Nombre / Organización]
>    Correo electrónico: [Tu Correo]
>    Finalidad: Análisis técnico y modelado de datos energéticos
>    
>    Agradezco de antemano su atención.
>    ```
> 4. Una vez recibido el correo con el token, abrir el archivo `.env` en la raíz de `EcoGrid_API`:
>    ```env
>    ESIOS_API_TOKEN=tu_token_aqui_sin_comillas
>    ```
> 5. Guardar el archivo. El panel web detectará de forma automática que el token está configurado y enviará la cabecera `Authorization: Token token="TU_TOKEN"`.

---

### B. Open-Meteo (Pronóstico y Viento Multinivel)
> [!TIP]
> **ESTADO: ACTIVO Y OPERATIVO (100% Funcional sin registro)**
> - La API de Open-Meteo (`api.open-meteo.com/v1/forecast`) es pública y no requiere clave de API para uso no comercial ni proyectos de desarrollo.
> - Parámetros configurados:
>   - Coordenadas Madrid: `latitude=40.41`, `longitude=-3.73`, `timezone=Europe/Madrid`.
>   - Variables eólicas: velocidad y dirección del viento a 4 alturas (`10m`, `80m`, `120m`, `180m`).
>   - Variables térmicas y de radiación: `temperature_2m`, `relative_humidity_2m`, `cloud_cover`, `direct_normal_irradiance`, `global_tilted_irradiance`, `shortwave_radiation`.
> - No se requiere ninguna acción manual adicional para esta fuente.

---

### C. OMIE (Operador del Mercado Ibérico de Energía)
> [!NOTE]
> **ESTADO: ACTIVO Y OPERATIVO (Descarga directa pública)**
> - La descarga de precios marginales horarios de casación del mercado diario (`marginalpdbc`) y curvas de oferta y demanda agregadas (`curva_pbc_uof`) se realiza directamente desde los repositorios públicos de publicación de OMIE (`https://www.omie.es/es/file-download`).
> - No requiere registro previo ni clave de API para acceder a los archivos diarios estándar.
> - Si OMIE llegara a exigir firma digital o certificado para descargas masivas o históricas en fases futuras, se documentará en este apartado.

---

## 🛠️ 2. ACCIONES INTERNAS (CONFIGURACIÓN Y EJECUCIÓN LOCAL)

### A. Preparación del Entorno
1. Abrir una terminal de PowerShell dentro del directorio raíz `EcoGrid_API`:
   ```powershell
   # Activar el entorno virtual
   .\venv\Scripts\Activate.ps1
   ```
2. Verificar las dependencias instaladas:
   ```powershell
   pip install -r requirements.txt
   ```

### B. Puesta en Marcha del Servidor Web
1. Iniciar el servidor local de desarrollo con Uvicorn:
   ```powershell
   uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Abrir en el navegador web:
   ```text
   http://127.0.0.1:8000
   ```

### C. Verificación de Almacenamiento Local
- Todos los datos brutos recibidos se guardan de forma local e independiente en:
  `data/raw/{origen}_{YYYYMMDD_HHMMSS}.json`
- Se pueden inspeccionar, previsualizar y descargar directamente desde la interfaz web o explorando la carpeta `data/raw/`.
