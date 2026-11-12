# ⚡ EcoGrid Analytics API - Gestor de Ingesta y Conectores

Plataforma web desarrollada en **Python** y **FastAPI** para la administración, orquestación y almacenamiento en bruto de datos energéticos y meteorológicos procedentes de:
- **Open-Meteo**: Datos meteorológicos horarios de Madrid con viento multinivel (10m a 180m), radiación solar y nubosidad.
- **OMIE**: Precios marginales horarios y curvas de casación del mercado eléctrico ibérico (España y Portugal).
- **REE / ESIOS**: Demanda eléctrica peninsular en tiempo real, prevista y programada de Red Eléctrica de España.

---

## 🚀 Inicio Rápido

1. **Activar entorno virtual**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. **Instalar dependencias**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Iniciar el servidor local**:
   ```powershell
   uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
4. **Abrir panel de control**:
   Navega a [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📚 Documentación

- **[RESUMEN_PROYECTO.md](file:///c:/Users/USER/Desktop/EcoGrid_API/RESUMEN_PROYECTO.md)**: Explicación detallada del árbol de archivos, diagrama de flujos de datos e instrucciones completas.
- **[acciones.md](file:///c:/Users/USER/Desktop/EcoGrid_API/acciones.md)**: Manual de registro y obtención de tokens de API (ESIOS REE) y notas técnicas de los orígenes.