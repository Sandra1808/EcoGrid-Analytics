# Obtención y preparación de los datos para el modelo EcoGrid

## 1. Objetivo del trabajo realizado

Para disponer de datos históricos con los que estudiar la demanda eléctrica, preparamos un pipeline en Python que recogió información de REE, OMIE y Open-Meteo y la reunió en un CSV horario. El primer objetivo del modelo fue la **demanda eléctrica real peninsular agregada de REE**, expresada en MW, para las próximas 24 horas.

El pipeline de extracción preparó los datos, pero **el entrenamiento se realizó posteriormente en un notebook separado**. Este documento describe lo que se hizo y los resultados observados, no un procedimiento de instalación.

## 2. Fuentes utilizadas

| Fuente | Datos extraídos | Origen consultado |
| --- | --- | --- |
| REE | Demanda real, prevista y programada; demanda programada total cuando la respuesta la incluía. | API pública APIdatos, endpoint de demanda en tiempo real: `https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real`. |
| OMIE | Precios marginales de electricidad de España y Portugal. | Ficheros diarios `marginalpdbc`, descargados mediante `https://www.omie.es/es/file-download`. |
| Open-Meteo | Temperatura, humedad, viento, dirección, nubosidad y radiación para un punto en Madrid (latitud 40,41; longitud -3,73). | API histórica: `https://archive-api.open-meteo.com/v1/archive`. |

La meteorología descargada corresponde al archivo histórico para un punto geográfico: no equivale a pronósticos meteorológicos históricos ni representa por sí sola a toda la península.

## 3. Herramienta y primeras comprobaciones

Se utilizó `EcoGrid_API\src\historical_pipeline.py`, ejecutándolo desde la carpeta `EcoGrid_API` con el Python del entorno virtual. Para evitar depender de la activación del entorno en PowerShell, se invocó directamente `.\.venv\Scripts\python.exe`.

Primero se comprobó cada fuente para el periodo de prueba del 8 de noviembre al 8 de diciembre de 2023:

```powershell
.\.venv\Scripts\python.exe -m src.historical_pipeline --start 2023-11-08 --end 2023-12-08 --sources ree
.\.venv\Scripts\python.exe -m src.historical_pipeline --start 2023-11-08 --end 2023-12-08 --sources weather
.\.venv\Scripts\python.exe -m src.historical_pipeline --start 2023-11-08 --end 2023-12-08 --sources omie
```

La prueba final de ese mes informó de **720 horas disponibles en cada una de las tres fuentes**. Cada ejecución reutilizó las respuestas de las otras fuentes que ya se encontraban en la caché y regeneró el CSV combinado.

## 4. Extracción del histórico completo

Después se ejecutó el intervalo de tres años:

```powershell
.\.venv\Scripts\python.exe -m src.historical_pipeline --start 2023-11-08 --end 2026-11-08 --sources ree,weather,omie
```

El inicio, **8 de noviembre de 2023**, se incluyó; el final, **8 de noviembre de 2026**, se excluyó. Ambos límites se interpretaron como días de `Europe/Madrid`. El proceso generó una rejilla de **26.304 horas UTC**, del 7 de noviembre de 2023 a las 23:00 UTC al 7 de noviembre de 2026 a las 22:00 UTC.

Las consultas de REE y Open-Meteo se organizaron en segmentos mensuales; OMIE se consultó por día. Se guardaron las respuestas originales en `EcoGrid_API\data\history\raw\ree`, `weather` y `omie`. Esta caché permitió reanudar el proceso y volver a generar los CSV sin repetir descargas ya disponibles. Los días que seguían sin respuesta se registraron como errores.

## 5. Normalización y construcción del CSV

El pipeline alineó los datos en un eje horario común UTC y generó una fila por hora:

1. Las observaciones de cada serie REE se agruparon por hora mediante su media. Para identificar una hora completa de demanda real se contaron 12 muestras.
2. Los periodos de precio OMIE, horarios o de 15 minutos según el fichero, se alinearon y promediaron por hora. La fecha del mercado se interpretó en `Europe/Madrid`.
3. Las variables meteorológicas se solicitaron por hora en UTC. Las velocidades del viento se pidieron en m/s.
4. Se añadieron `year`, `month`, `day` y `hour` a partir de la fecha UTC. Las ausencias se dejaron vacías: no se inventaron valores ni se sustituyeron por cero.

El CSV final adoptó las **25 columnas del encabezado del archivo de referencia**: `time`, 14 variables meteorológicas, cuatro columnas de calendario, dos precios OMIE y cuatro series de demanda REE. La guía de referencia mencionaba 26 columnas, pero el encabezado del CSV tenía 25.

## 6. Archivos generados y cobertura

Los archivos de la extracción completa quedaron en `EcoGrid_API\data\history\processed\`:

- `training_dataset_2023-11-08_2026-11-08.csv`: maestro con las 26.304 horas, incluidas aquellas con valores ausentes.
- `training_dataset_2023-11-08_2026-11-08_demand_valid.csv`: subconjunto de **26.251 filas** con 12 muestras de demanda real, demanda prevista y programada y variables meteorológicas base presentes.
- `quality_report_2023-11-08_2026-11-08.json`: informe con la cobertura, los errores y los recuentos por columna.

El informe se consultó con:

```powershell
Get-Content .\data\history\processed\quality_report_2023-11-08_2026-11-08.json
```

El resultado registrado fue el siguiente:

| Comprobación | Resultado |
| --- | --- |
| Demanda real REE | 26.258 horas con valor; 46 ausentes y 7 con muestras parciales. |
| Precios OMIE | 26.256 horas con valor; 48 ausentes por respuestas 404 de los días 30 de octubre y 27 de noviembre de 2025. |
| Meteorología | 26.304 horas para las variables principales; velocidad y dirección de viento a 180 m sin valores en el rango. |
| Demanda programada total | 7.968 valores presentes; los restantes quedaron vacíos. |

El subconjunto `_demand_valid` no exigió los precios OMIE ni las dos columnas de viento a 180 m. Las siete pruebas del pipeline se ejecutaron con `.\.venv\Scripts\python.exe -m unittest discover -s tests` y finalizaron correctamente. Esas pruebas no entrenaron el modelo.

## 7. Relación con el notebook de entrenamiento

En el notebook `EcoGrid_Entrenamiento_Modelo_Demanda.ipynb`, el archivo cargado se denominó `training_dataset_2023-11-08_2026-11-08_V2.csv`. Sus resultados guardados mostraron **26.304 filas y 25 columnas**, con el mismo periodo y recuentos de ausencias que el maestro generado. Sin embargo, no se recibió ese archivo V2 para compararlo directamente, por lo que **no se puede confirmar que sea exactamente el mismo fichero**.

El notebook trabajó con el histórico completo, no con el CSV `_demand_valid`. Creó una rejilla horaria, no interpoló la demanda real y generó variables de calendario y retardos de demanda de 24 y 168 horas. Dejó fuera meteorología, precios y previsiones REE para evitar usar información futura. Tras descartar filas sin los valores necesarios, obtuvo **26.006 filas** para modelado y las dividió cronológicamente en entrenamiento, validación y prueba.

Según las salidas guardadas en el notebook, se entrenó un modelo XGBoost y se comparó con un baseline de demanda de 24 horas antes. En el periodo de prueba, el MAE registrado fue de **1.283 MW** para XGBoost y **1.972 MW** para el baseline. El notebook guardó un modelo `.joblib`, las variables y las métricas en el entorno de Colab; estos artefactos no estaban incluidos con el notebook recibido.

La predicción de 24 horas mostrada en esa ejecución se generó a partir de un histórico que terminaba el 7 de noviembre de 2026. Como el notebook se ejecutó después, la propia salida advirtió de que el periodo predicho ya podía estar en el pasado. Para una predicción operativa, los datos de demanda deben estar actualizados.

## 8. Limitaciones y alcance

La disponibilidad de un valor en el CSV no implica que se conociera en el momento de emitir una predicción. Por eso el notebook no utilizó meteorología observada futura ni precios o previsiones REE cuya disponibilidad histórica no se había comprobado. Los resultados corresponden a la ejecución guardada en el notebook; no se ha verificado aquí la identidad exacta del fichero V2 ni se han vuelto a ejecutar sus métricas.

Los datos históricos y las cachés se guardaron localmente y están ignorados por Git en `EcoGrid_API`. Compartir código o commits no los sube automáticamente al repositorio remoto.
