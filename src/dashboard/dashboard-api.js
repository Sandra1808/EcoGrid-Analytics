import { apiService } from './apiService.js';

document.addEventListener('DOMContentLoaded', async () => {
    const comunidadSelect = document.getElementById('comunidadSelect');
    const fechaInput = document.getElementById('fechaInput');
    const errorContainer = document.getElementById('errorContainer'); 
    
    const btnTogglePrediccion = document.getElementById('btnTogglePrediccion'); 
    if (btnTogglePrediccion) {
        btnTogglePrediccion.addEventListener('click', () => {
            const datasetPredicha = demandChart.data.datasets[1]; // El índice 1 es la predicha
            datasetPredicha.hidden = !datasetPredicha.hidden;
            demandChart.update();
            btnTogglePrediccion.textContent = datasetPredicha.hidden ? 'Mostrar Curva Predicha' : 'Ocultar Curva Predicha';
        });
    }

    const btnReejecutarIA = document.getElementById('btnReejecutarIA');
    if (btnReejecutarIA) {
        btnReejecutarIA.addEventListener('click', async () => {
            try {
                clearError();
                await apiService.triggerPrediction();
                alert('Solicitud de re-ejecución de predicción enviada correctamente.');
                loadDashboardData(); // Recarga los datos
            } catch (error) {
                showError(`Error al re-ejecutar la predicción: ${error.message}`);
            }
        });
    }

    // Declaramos la instancia del gráfico para que sea accesible al actualizar datos
    const demandChart = new Chart(document.getElementById('demandChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { label: 'Demanda Real (MW)', data: [], borderColor: '#3b82f6' },
                { label: 'Demanda Predicha (MW)', data: [], borderColor: '#10b981' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // ÚNICA función de renderizado asociada al gráfico 
    function renderDemandChart(seriesData) {
        if (!Array.isArray(seriesData)) {
            throw new Error('La API devolvió un formato de serie no válido');
        }
        const points = seriesData
            .map(point => ({
                timestamp: Date.parse(point.fecHora),
                real: point.demandaRealMWH == null ? null : Number(point.demandaRealMWH),
                predicted: point.demandaPredichaMWH == null ? null : Number(point.demandaPredichaMWH)
            }))
            .filter(point => Number.isFinite(point.timestamp))
            .sort((a, b) => a.timestamp - b.timestamp);

        demandChart.data.labels = points.map(point =>
            new Date(point.timestamp).toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/Madrid'
            })
        );
        demandChart.data.datasets[0].data = points.map(point => point.real);
        demandChart.data.datasets[1].data = points.map(point => point.predicted);
        demandChart.update();
    }

    // Cogemos la fecha actual para el input de la fecha, en formato YYYY-MM-DD
    const now = new Date();
    const todayStr = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, '0'),
        String(now.getDate()).padStart(2, '0')
    ].join('-');
    if (fechaInput) fechaInput.value = todayStr;

    // 1. Cargar el desplegable de Comunidades Autónomas (con parada si falla o está vacío)
    try {
        const comunidades = await apiService.getComunidades();
        if (!Array.isArray(comunidades) || comunidades.length === 0) {
            throw new Error('La lista de comunidades autónomas está vacía.');
        }

        if (comunidadSelect) {
            comunidadSelect.replaceChildren();

            for (const ccaa of comunidades) {
                const option = document.createElement('option');
                option.value = String(ccaa.id);
                option.textContent = ccaa.nombre;
                comunidadSelect.appendChild(option);
            }

            comunidadSelect.value = String(comunidades[0].id);
        }
    } catch (error) {
        console.error('Error al cargar comunidades:', error);
        showError('No se pudieron cargar las comunidades autónomas desde el servidor.');
        return; // Detenemos la ejecución para evitar que el dashboard intente cargar sin CCAA válida
    }

    // 2. Función principal para cargar y refrescar los datos del Dashboard
    async function loadDashboardData() {
        const fechaSeleccionada = fechaInput ? fechaInput.value : todayStr;
        const ccaaSeleccionada = comunidadSelect ? comunidadSelect.value : '';

        try {
            clearError();

            // Llamadas a la API en paralelo (incluyendo los endpoints auxiliares)
            const [summary, demandSeries, alerts, sources, rawFiles, tasks] = await Promise.all([
                apiService.getDashboardSummary(fechaSeleccionada, ccaaSeleccionada),
                apiService.getDemandSeries(fechaSeleccionada, ccaaSeleccionada),
                apiService.getAlerts(),
                apiService.getSources().catch(() => []),
                apiService.getRawFiles().catch(() => []),
                apiService.getSchedulerTasks().catch(() => [])
            ]);

            // Renderizar componentes principales
            renderSummaryKPIs(summary);
            renderDemandChart(demandSeries);
            renderAlerts(alerts);
            
            // Renderizar auxiliares si tienes contenedores habilitados en el HTML
            renderSources(sources);
            renderRawFiles(rawFiles);
            renderTasks(tasks);

        } catch (error) {
            console.error('Error al sincronizar con la API:', error);
            showError(`Error de conexión o de la API: ${error.message}`);
        }
    }

    // 3. Funciones de renderizado en el DOM
    function renderSummaryKPIs(summary) {
        const kpis = summary?.kpis ?? {};
        const format = (value, suffix) => {
            const number = value == null ? NaN : Number(value);
            return Number.isFinite(number)
                ? `${number.toLocaleString('es-ES')} ${suffix}`
                : 'Sin datos disponibles';
        };

        const demActualEl = document.getElementById('kpiDemandaActual');
        if (demActualEl) demActualEl.textContent = format(kpis.demanda_media_mw, 'MW');
        
        const demPrevEl = document.getElementById('kpiDemandaPrevista');
        if (demPrevEl) demPrevEl.textContent = 'Sin datos disponibles';
        
        const costeDesvioEl = document.getElementById('kpiCosteDesvio');
        if (costeDesvioEl) costeDesvioEl.textContent = format(kpis.coste_desvio_estimado_eur, '€');
        
        const costeFinancieroEl = document.getElementById('kpiCosteDesvioFinanciero');
        if (costeFinancieroEl) {
            costeFinancieroEl.textContent = format(kpis.coste_desvio_estimado_eur, '€');
        }
    }

    function renderAlerts(alerts) {
        const container = document.getElementById('alertsContainer');
        if (!container) return;

        container.replaceChildren();

        if (!Array.isArray(alerts) || alerts.length === 0) {
            container.textContent = 'Sin alertas activas registradas.';
            return;
        }

        for (const alert of alerts) {
            const item = document.createElement('p');
            item.textContent = `[${alert.nivelAlerta ?? '—'}] ${alert.tipo ?? ''} ${alert.mensaje ?? ''} ${alert.fecHora ?? ''}`;
            container.appendChild(item);
        }
    }

    // Renderizadores opcionales para los endpoints auxiliares (si existen en tu HTML)
    function renderSources(sources) {
        const container = document.getElementById('sourcesContainer');
        if (!container) return;
        container.replaceChildren();
        if (!Array.isArray(sources) || sources.length === 0) {
            container.textContent = 'Sin fuentes registradas.';
            return;
        }
        for (const src of sources) {
            const p = document.createElement('p');
            p.textContent = `Fuente: ${src.nombre ?? src.id ?? '—'}`;
            container.appendChild(p);
        }
    }

    function renderRawFiles(files) {
        const container = document.getElementById('rawFilesContainer');
        if (!container) return;
        container.replaceChildren();
        if (!Array.isArray(files) || files.length === 0) {
            container.textContent = 'Sin ficheros raw.';
            return;
        }
        for (const file of files) {
            const p = document.createElement('p');
            p.textContent = `Fichero: ${file.nombre ?? file.id ?? '—'}`;
            container.appendChild(p);
        }
    }

    function renderTasks(tasks) {
        const container = document.getElementById('tasksContainer');
        if (!container) return;
        container.replaceChildren();
        if (!Array.isArray(tasks) || tasks.length === 0) {
            container.textContent = 'Sin tareas programadas.';
            return;
        }
        for (const task of tasks) {
            const p = document.createElement('p');
            p.textContent = `Tarea: ${task.nombre ?? task.id ?? '—'} (${task.estado ?? 'Activa'})`;
            container.appendChild(p);
        }
    }

    function showError(message) {
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
        }
    }

    function clearError() {
        if (errorContainer) {
            errorContainer.textContent = '';
            errorContainer.style.display = 'none';
        }
    }

    // Eventos de cambio en los filtros
    if (comunidadSelect) comunidadSelect.addEventListener('change', loadDashboardData);
    if (fechaInput) fechaInput.addEventListener('change', loadDashboardData);

    // Carga inicial al abrir la página
    loadDashboardData();
});