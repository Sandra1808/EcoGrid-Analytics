import { apiService } from './apiService.js';

document.addEventListener('DOMContentLoaded', async () => {
    let usuario;

    try {
        usuario = await apiService.getCurrentUser();
    } catch (error) {
        window.location.replace('index.html');
        return;
    }

    const comunidadSelect = document.getElementById('comunidadSelect');
    const fechaInput = document.getElementById('fechaInput');
    const errorContainer = document.getElementById('errorContainer');

    const toggleFiltersBtn = document.getElementById('toggleFiltersBtn');
    const filterDropdown = document.getElementById('filterDropdown');
    const arrowIcon = document.getElementById('arrowIcon');

    const activeModelName = document.getElementById('activeModelName');
    const activeModelVersion = document.getElementById('activeModelVersion');

    toggleFiltersBtn?.addEventListener('click', () => {
        if (!filterDropdown) return;

        const abierto = filterDropdown.classList.toggle('show');

        if (arrowIcon) {
            arrowIcon.style.transform = abierto ? 'rotate(180deg)' : '';
        }
    });

    const userNameDisplay = document.getElementById('userNameDisplay');
    if (userNameDisplay) {
        userNameDisplay.textContent = usuario.nombre || usuario.email || '';
    }

    const adminLink = document.getElementById('adminLink');
    const rol = (usuario.rol || '').toUpperCase();

    if (adminLink) {
        adminLink.style.display =
            rol === 'ADMIN' || rol === 'ADMINISTRADOR' ? 'inline' : 'none';
    }

    const logoutLink = document.getElementById('logoutLink');
    if (logoutLink) {
        logoutLink.addEventListener('click', async (event) => {
            event.preventDefault();

            try {
                await apiService.logout();
                window.location.replace('index.html');
            } catch (error) {
                showError(`No se pudo cerrar la sesión: ${error.message}`);
            }
        });
    }

    const chartCanvas = document.getElementById('demandChart');
    if (!chartCanvas) {
        showError('No se encontró el elemento demandChart en el HTML.');
        return;
    }

    const demandChart = new Chart(chartCanvas, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Demanda Real (MW)',
                    data: [],
                    borderColor: '#3b82f6'
                },
                {
                    label: 'Demanda Predicha (MW)',
                    data: [],
                    borderColor: '#10b981'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });

    function renderDemandChart(seriesData) {
        if (!Array.isArray(seriesData)) {
            throw new Error('La API devolvió un formato de serie no válido');
        }

        const points = seriesData
            .map(point => ({
                timestamp: Date.parse(point.fecHora),
                real: point.demandaRealMWH == null
                    ? null
                    : Number(point.demandaRealMWH),
                predicted: point.demandaPredichaMWH == null
                    ? null
                    : Number(point.demandaPredichaMWH)
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

    function renderErrorMetrics(seriesData) {
        const maeEl = document.getElementById('valMAE');
        const rmseEl = document.getElementById('valRMSE');
        const mapeEl = document.getElementById('valMAPE');

        if (!Array.isArray(seriesData)) {
            if (maeEl) maeEl.textContent = '-- MW';
            if (rmseEl) rmseEl.textContent = '-- MW';
            if (mapeEl) mapeEl.textContent = '-- %';
            return;
        }

        const pairs = [];

        for (const point of seriesData) {
            if (
                point.demandaRealMWH == null ||
                point.demandaPredichaMWH == null
            ) {
                continue;
            }

            const real = Number(point.demandaRealMWH);
            const predicted = Number(point.demandaPredichaMWH);

            if (Number.isFinite(real) && Number.isFinite(predicted)) {
                pairs.push({ real, predicted });
            }
        }

        if (pairs.length === 0) {
            if (maeEl) maeEl.textContent = '-- MW';
            if (rmseEl) rmseEl.textContent = '-- MW';
            if (mapeEl) mapeEl.textContent = '-- %';
            return;
        }

        const errors = pairs.map(point =>
            Math.abs(point.real - point.predicted)
        );

        const mae = errors.reduce((sum, error) => sum + error, 0) / pairs.length;
        const rmse = Math.sqrt(
            errors.reduce((sum, error) => sum + error ** 2, 0) / pairs.length
        );

        const mapePairs = pairs.filter(point => point.real !== 0);
        const mape = mapePairs.length > 0
            ? mapePairs.reduce(
                (sum, point) =>
                    sum +
                    Math.abs(point.real - point.predicted) /
                        Math.abs(point.real),
                0
            ) / mapePairs.length * 100
            : null;

        const format = value => value.toLocaleString('es-ES', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        if (maeEl) {
            maeEl.textContent = `${format(mae)} MW`;
        }

        if (rmseEl) {
            rmseEl.textContent = `${format(rmse)} MW`;
        }

        if (mapeEl) {
            mapeEl.textContent = mape === null
                ? '-- %'
                : `${format(mape)} %`;
        }
    }

    function getAverageForecast(seriesData) {
        if (!Array.isArray(seriesData)) {
            return null;
        }

        const predictions = seriesData
            .map(point => point.demandaPredichaMWH)
            .filter(value => value != null)
            .map(Number)
            .filter(Number.isFinite);

        if (predictions.length === 0) {
            return null;
        }

        return predictions.reduce((sum, value) => sum + value, 0) /
            predictions.length;
    }

    async function loadActiveModel() {
        if (!activeModelName && !activeModelVersion) {
            return;
        }

        try {
            const model = await apiService.getActiveModel();

            if (!model || typeof model !== 'object') {
                throw new Error('La API devolvió un modelo activo no válido');
            }

            if (activeModelName) {
                activeModelName.textContent =
                    model.nombreAlgoritmo || 'Sin nombre';
            }

            if (activeModelVersion) {
                activeModelVersion.textContent =
                    model.version ? `Versión ${model.version}` : 'Versión —';
            }
        } catch (error) {
            console.error('Error al cargar el modelo activo:', error);

            if (activeModelName) {
                activeModelName.textContent = 'No disponible';
            }

            if (activeModelVersion) {
                activeModelVersion.textContent = 'Error al consultar la API';
            }
        }
    }

    const now = new Date();
    const todayStr = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, '0'),
        String(now.getDate()).padStart(2, '0')
    ].join('-');

    if (fechaInput) {
        fechaInput.value = todayStr;
    }

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

            const nacional = comunidades.find(ccaa => Number(ccaa.id) === 1);

            if (!nacional) {
                throw new Error('No se encontró España nacional (IDCCAA=1)');
            }

            comunidadSelect.value = String(nacional.id);
        }
    } catch (error) {
        console.error('Error al cargar comunidades:', error);
        showError(`No se pudieron cargar las comunidades autónomas: ${error.message}`);
        return;
    }

    async function loadDashboardData() {
        const fechaSeleccionada = fechaInput ? fechaInput.value : todayStr;
        const ccaaSeleccionada = comunidadSelect ? comunidadSelect.value : '';

        try {
            clearError();

            const [summary, demandSeries, alerts, sources, rawFiles, tasks] =
                await Promise.all([
                    apiService.getDashboardSummary(
                        fechaSeleccionada,
                        ccaaSeleccionada
                    ),
                    apiService.getDemandSeries(
                        fechaSeleccionada,
                        ccaaSeleccionada
                    ),
                    apiService.getAlerts(),
                    apiService.getSources(),
                    apiService.getRawFiles(),
                    apiService.getSchedulerTasks()
                ]);

            renderSummaryKPIs(summary, demandSeries);
            renderDemandChart(demandSeries);
            renderErrorMetrics(demandSeries);
            renderAlerts(alerts);
            renderSources(sources);
            renderRawFiles(rawFiles);
            renderTasks(tasks);
        } catch (error) {
            console.error('Error al sincronizar con la API:', error);
            showError(`Error de conexión o de la API: ${error.message}`);
        }
    }

    function renderSummaryKPIs(summary, demandSeries) {
        const kpis = summary?.kpis ?? {};

        const format = (value, suffix) => {
            const number = value == null ? NaN : Number(value);

            return Number.isFinite(number)
                ? `${number.toLocaleString('es-ES')} ${suffix}`
                : 'Sin datos disponibles';
        };

        const demActualEl = document.getElementById('kpiDemandaActual');
        if (demActualEl) {
            demActualEl.textContent = format(kpis.demanda_media_mw, 'MW');
        }

        const demPrevEl = document.getElementById('kpiDemandaPrevista');
        if (demPrevEl) {
            demPrevEl.textContent =
                format(getAverageForecast(demandSeries), 'MW');
        }

        const costeDesvioEl = document.getElementById('kpiCosteDesvio');
        if (costeDesvioEl) {
            costeDesvioEl.textContent =
                format(kpis.coste_desvio_estimado_eur, '€');
        }

        const costeFinancieroEl =
            document.getElementById('kpiCosteDesvioFinanciero');

        if (costeFinancieroEl) {
            costeFinancieroEl.textContent =
                format(kpis.coste_desvio_estimado_eur, '€');
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
            item.textContent =
                `[${alert.nivelAlerta ?? '—'}] ${alert.tipo ?? ''} ` +
                `${alert.mensaje ?? ''} ${alert.fecHora ?? ''}`;
            container.appendChild(item);
        }
    }

    function renderSources(sources) {
        const container = document.getElementById('sourcesContainer');
        if (!container) return;

        container.replaceChildren();

        if (!Array.isArray(sources) || sources.length === 0) {
            container.textContent = 'Sin fuentes registradas.';
            return;
        }

        for (const src of sources) {
            const paragraph = document.createElement('p');
            paragraph.textContent = `Fuente: ${src.nombre ?? src.id ?? '—'}`;
            container.appendChild(paragraph);
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
            const paragraph = document.createElement('p');
            paragraph.textContent =
                `Fichero: ${file.nombre ?? file.id ?? '—'}`;
            container.appendChild(paragraph);
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
            const paragraph = document.createElement('p');
            paragraph.textContent =
                `Tarea: ${task.nombre ?? task.id ?? '—'} ` +
                `(${task.estado ?? 'Activa'})`;
            container.appendChild(paragraph);
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

    if (comunidadSelect) {
        comunidadSelect.addEventListener('change', loadDashboardData);
    }

    if (fechaInput) {
        fechaInput.addEventListener('change', loadDashboardData);
    }

    loadActiveModel();
    loadDashboardData();
});