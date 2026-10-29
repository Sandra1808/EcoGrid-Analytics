/**
 * EcoGrid Analytics Enterprise - Panel de Control & Operación
 * Lógica JavaScript interactiva, autenticación de operador, ingesta y automatizador (APScheduler)
 */

document.addEventListener('DOMContentLoaded', () => {
  // Inicialización del estado de autenticación corporativa
  checkAuthSession();

  // Atajos de teclado y accesibilidad
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllModals();
    }
  });

  // Cierre de modales al hacer clic sobre el fondo
  const modals = document.querySelectorAll('.modal-overlay');
  modals.forEach((modal) => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  });

  // Si ya está autenticado, cargar las tareas programadas periódicamente en segundo plano
  if (sessionStorage.getItem('ecogrid_authenticated') === 'true') {
    loadScheduledTasks();
  }
});

/* ==========================================================================
   1. CONTROL DE AUTENTICACIÓN (LOGIN OPERADOR)
   ========================================================================== */

/**
 * Comprueba si el operador tiene una sesión activa en sessionStorage.
 */
function checkAuthSession() {
  const isAuthenticated = sessionStorage.getItem('ecogrid_authenticated') === 'true';
  const loginScreen = document.getElementById('login-screen');
  const dashboardApp = document.getElementById('dashboard-app');

  if (isAuthenticated) {
    if (loginScreen) loginScreen.style.display = 'none';
    if (dashboardApp) dashboardApp.style.display = 'block';
  } else {
    if (loginScreen) loginScreen.style.display = 'flex';
    if (dashboardApp) dashboardApp.style.display = 'none';
  }
}

/**
 * Procesa el formulario de autenticación estricta (admin / admin).
 */
function handleLoginSubmit(event) {
  event.preventDefault();
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  const errorAlert = document.getElementById('login-error-alert');
  const errorText = document.getElementById('login-error-text');

  const username = usernameInput ? usernameInput.value.trim() : '';
  const password = passwordInput ? passwordInput.value : '';

  // Validación estricta hardcodeada
  if (username === 'admin' && password === 'admin') {
    if (errorAlert) errorAlert.style.display = 'none';
    sessionStorage.setItem('ecogrid_authenticated', 'true');
    checkAuthSession();
    loadScheduledTasks();
    showToast('Sesión de operador iniciada correctamente (admin)', 'success');
  } else {
    if (errorAlert) {
      errorAlert.style.display = 'flex';
      errorText.textContent = 'Credenciales no autorizadas. Usuario o clave incorrectos.';
    }
    if (passwordInput) {
      passwordInput.value = '';
      passwordInput.focus();
    }
  }
}

/**
 * Cierra la sesión activa del operador.
 */
function handleLogout() {
  sessionStorage.removeItem('ecogrid_authenticated');
  checkAuthSession();
  showToast('Sesión de operador finalizada', 'info');
}

/* ==========================================================================
   2. NAVEGACIÓN POR PESTAÑAS (TABS)
   ========================================================================== */

/**
 * Cambia entre la vista de Ingesta Manual y el Automatizador de Tareas.
 */
function switchMainTab(tabName) {
  const tabManualBtn = document.getElementById('tab-btn-manual');
  const tabSchedBtn = document.getElementById('tab-btn-scheduler');
  const viewManual = document.getElementById('view-manual');
  const viewScheduler = document.getElementById('view-scheduler');

  if (tabName === 'manual') {
    if (tabManualBtn) tabManualBtn.classList.add('active');
    if (tabSchedBtn) tabSchedBtn.classList.remove('active');
    if (viewManual) viewManual.style.display = 'block';
    if (viewScheduler) viewScheduler.style.display = 'none';
  } else if (tabName === 'scheduler') {
    if (tabSchedBtn) tabSchedBtn.classList.add('active');
    if (tabManualBtn) tabManualBtn.classList.remove('active');
    if (viewManual) viewManual.style.display = 'none';
    if (viewScheduler) viewScheduler.style.display = 'block';
    loadScheduledTasks();
  }
}

/* ==========================================================================
   3. GESTIÓN DE ORÍGENES Y CONECTORES MANUALES
   ========================================================================== */

/**
 * Activa o desactiva un origen de datos dinámicamente.
 */
async function toggleSource(sourceId, isChecked) {
  const card = document.getElementById(`card-${sourceId}`);
  try {
    const res = await fetch(`/api/sources/${sourceId}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: isChecked })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      if (isChecked) {
        card.classList.add('card-active');
        card.classList.remove('card-inactive');
        showToast(`Conector "${data.source.name}" habilitado`, 'success');
      } else {
        card.classList.remove('card-active');
        card.classList.add('card-inactive');
        showToast(`Conector "${data.source.name}" deshabilitado`, 'info');
      }
      updateKpis();
    } else {
      throw new Error(data.detail || 'Error al modificar estado del conector');
    }
  } catch (err) {
    console.error(err);
    showToast(`Error: ${err.message}`, 'error');
    const toggle = document.getElementById(`toggle-${sourceId}`);
    if (toggle) toggle.checked = !isChecked;
  }
}

/**
 * Dispara la ejecución manual de un solo conector.
 */
async function executeSource(sourceId) {
  const btn = document.getElementById(`btn-run-${sourceId}`);
  const spinner = btn ? btn.querySelector('.loader-spinner') : null;
  const icon = btn ? btn.querySelector('.btn-icon') : null;

  try {
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';
    if (icon) icon.style.display = 'none';

    showToast(`Iniciando llamada al conector ${sourceId}...`, 'info');

    const res = await fetch(`/api/sources/${sourceId}/execute`, {
      method: 'POST'
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Ingesta exitosa. Archivo persistido: ${data.result.saved_file}`, 'success');
      updateSourceCardStatus(sourceId, data.result);
      await loadRawFiles();
      await updateKpis();
    } else {
      const errMsg = (data.result && data.result.error) || data.detail || 'Fallo en la llamada';
      showToast(`Error en la llamada: ${errMsg}`, 'error');
      if (data.result) {
        updateSourceCardStatus(sourceId, data.result);
      }
    }
  } catch (err) {
    console.error(err);
    showToast(`Error de conexión con ${sourceId}: ${err.message}`, 'error');
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.style.display = 'none';
    if (icon) icon.style.display = 'inline-block';
  }
}

/**
 * Dispara la ingesta simultánea de todas las fuentes que estén activas.
 */
async function executeActiveSources() {
  const btn = document.getElementById('btn-execute-all');
  const spinner = btn ? btn.querySelector('.loader-spinner') : null;
  const icon = btn ? btn.querySelector('.btn-icon') : null;
  const label = btn ? btn.querySelector('.btn-label') : null;

  try {
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';
    if (icon) icon.style.display = 'none';
    if (label) label.textContent = 'Procesando Ingestas...';

    showToast('Ejecutando ingesta en paralelo de fuentes activas...', 'info');

    const res = await fetch('/api/ingestion/execute-active', {
      method: 'POST'
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Ingesta finalizada: ${data.total_success}/${data.total_executed} correctas`, 'success');
      if (data.results) {
        data.results.forEach((r) => {
          updateSourceCardStatus(r.source_id, r);
        });
      }
      await loadRawFiles();
      await updateKpis();
    } else {
      throw new Error(data.detail || 'Fallo en la ejecución masiva');
    }
  } catch (err) {
    console.error(err);
    showToast(`Error en la ingesta activa: ${err.message}`, 'error');
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.style.display = 'none';
    if (icon) icon.style.display = 'inline-block';
    if (label) label.textContent = 'Ejecutar Ingesta de Fuentes Activas';
  }
}

/**
 * Actualiza visualmente el bloque de estado de una tarjeta de origen.
 */
function updateSourceCardStatus(sourceId, result) {
  const panel = document.getElementById(`status-panel-${sourceId}`);
  if (!panel) return;

  const isSuccess = result.success || result.status === 'SUCCESS';
  const badgeHtml = isSuccess
    ? `<span class="badge badge-success">HTTP ${result.http_code || 200} OK</span>`
    : `<span class="badge badge-error">HTTP ${result.http_code || 0} ERROR</span>`;

  const timeFormatted = result.timestamp ? result.timestamp.replace('T', ' ').substring(0, 19) : 'Reciente';

  panel.innerHTML = `
    <div class="status-panel-header">
      <span class="status-panel-title">Última Ejecución</span>
      ${badgeHtml}
    </div>
    <div class="status-details">
      <div class="status-row">
        <span class="label">Marca Temporal:</span>
        <span class="val font-mono">${timeFormatted}</span>
      </div>
      ${result.saved_file ? `
      <div class="status-row">
        <span class="label">Archivo Local:</span>
        <span class="val font-mono text-cyan">${result.saved_file}</span>
      </div>` : ''}
      <div class="status-summary-text">
        ${result.summary || result.error || (isSuccess ? 'Respuesta procesada correctamente' : 'Error en la llamada')}
      </div>
    </div>
  `;
}

/**
 * Recarga y refresca el catálogo de fuentes desde la API.
 */
async function loadSources() {
  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    if (res.ok && data.sources) {
      data.sources.forEach((src) => {
        const toggle = document.getElementById(`toggle-${src.id}`);
        const card = document.getElementById(`card-${src.id}`);
        if (toggle) toggle.checked = src.active;
        if (card) {
          if (src.active) {
            card.classList.add('card-active');
            card.classList.remove('card-inactive');
          } else {
            card.classList.remove('card-active');
            card.classList.add('card-inactive');
          }
        }
        if (src.last_run) {
          updateSourceCardStatus(src.id, src.last_run);
        }
      });
      showToast('Estado de conectores actualizado', 'info');
      updateKpis();
    }
  } catch (err) {
    console.error(err);
  }
}

/* ==========================================================================
   4. AUTOMATIZADOR Y PLANIFICADOR DE TAREAS (APSCHEDULER ENGINE)
   ========================================================================== */

/**
 * Consulta y recarga la lista de tareas programadas desde /api/scheduler/tasks.
 */
async function loadScheduledTasks() {
  const tbody = document.getElementById('scheduled-tasks-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/scheduler/tasks');
    const data = await res.json();

    if (res.ok && data.tasks) {
      // Actualizar KPIs de planificador
      const kpiStatus = document.getElementById('sched-kpi-status');
      const kpiEnabled = document.getElementById('sched-kpi-enabled-count');
      const kpiTz = document.getElementById('sched-kpi-tz');

      if (kpiStatus && data.status) {
        kpiStatus.textContent = data.status.running ? 'En Ejecución (Activo)' : 'Detenido';
      }
      if (kpiEnabled && data.status) {
        kpiEnabled.textContent = `${data.status.enabled_tasks} / ${data.status.total_tasks}`;
      }
      if (kpiTz && data.status) {
        kpiTz.textContent = data.status.timezone || 'Europe/Madrid';
      }

      // Renderizar filas de la tabla
      tbody.innerHTML = data.tasks.map((t) => {
        const isEnabled = t.enabled;
        const nextRunBadge = (isEnabled && t.next_run)
          ? `<div class="next-run-badge font-mono">
               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                 <circle cx="12" cy="12" r="10"></circle>
                 <polyline points="12 6 12 12 16 14"></polyline>
               </svg>
               <span id="next-run-text-${t.id}">${t.next_run}</span>
             </div>`
          : `<span class="badge badge-neutral">En Pausa (Desactivada)</span>`;

        let lastRunHtml = `<span class="text-muted font-italic">Sin ejecuciones previas</span>`;
        if (t.last_run) {
          const isSuccess = t.last_run.status === 'SUCCESS';
          const badgePill = isSuccess
            ? `<span class="badge badge-success">HTTP ${t.last_run.http_code || 200} OK</span>`
            : `<span class="badge badge-error">HTTP ${t.last_run.http_code || 0} ERROR</span>`;

          lastRunHtml = `
            <div class="last-run-timestamp font-mono">${t.last_run.timestamp}</div>
            ${badgePill}
            ${t.last_run.saved_file ? `<div class="font-mono text-cyan file-tag">${t.last_run.saved_file}</div>` : ''}
          `;
        }

        return `
          <tr id="sched-row-${t.id}" class="${!isEnabled ? 'row-task-disabled' : ''}">
            <td>
              <label class="toggle-switch" title="Activar / Desactivar Tarea Programada">
                <input type="checkbox" id="sched-toggle-${t.id}" ${isEnabled ? 'checked' : ''} onchange="toggleScheduledTask('${t.id}', this.checked)">
                <span class="slider"></span>
              </label>
            </td>
            <td>
              <div class="task-cell-title">
                <strong>${t.name}</strong>
                <span class="badge badge-source-${t.connector}">${t.connector}</span>
              </div>
              <div class="task-cell-desc">${t.description}</div>
              <div class="task-cell-meta">Destino: <code>${t.destination_dir}/</code></div>
            </td>
            <td>
              <div class="interval-editor-group">
                <div class="interval-input-wrapper">
                  <input type="number" id="interval-input-${t.id}" class="form-input-number" min="1" max="1440" value="${t.interval_minutes}">
                  <span class="interval-unit">min</span>
                </div>
                <button class="btn btn-secondary btn-xs" title="Guardar intervalo" onclick="updateScheduledTaskInterval('${t.id}')">
                  <span>Guardar</span>
                </button>
              </div>
              <span class="font-mono text-muted cron-preview">CRON: ${t.cron}</span>
            </td>
            <td>${lastRunHtml}</td>
            <td>${nextRunBadge}</td>
            <td class="text-right table-actions">
              <button class="btn btn-outline btn-sm" id="btn-run-task-${t.id}" onclick="executeScheduledTaskNow('${t.id}')">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                <span>Ejecutar Ahora</span>
                <span class="loader-spinner" style="display: none;"></span>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Error al cargar tareas planificadas:', err);
  }
}

/**
 * Activa o desactiva dinámicamente una tarea programada.
 */
async function toggleScheduledTask(taskId, isChecked) {
  const row = document.getElementById(`sched-row-${taskId}`);
  try {
    const res = await fetch(`/api/scheduler/tasks/${taskId}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: isChecked })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      if (isChecked) {
        if (row) row.classList.remove('row-task-disabled');
        showToast(`Tarea programada "${taskId}" activada`, 'success');
      } else {
        if (row) row.classList.add('row-task-disabled');
        showToast(`Tarea programada "${taskId}" pausada`, 'info');
      }
      await loadScheduledTasks();
    } else {
      throw new Error(data.detail || 'No se pudo cambiar el estado de la tarea');
    }
  } catch (err) {
    console.error(err);
    showToast(`Error: ${err.message}`, 'error');
    const toggle = document.getElementById(`sched-toggle-${taskId}`);
    if (toggle) toggle.checked = !isChecked;
  }
}

/**
 * Actualiza la frecuencia en minutos de una tarea programada y persiste en tasks.yaml.
 */
async function updateScheduledTaskInterval(taskId) {
  const input = document.getElementById(`interval-input-${taskId}`);
  const val = input ? parseInt(input.value, 10) : 0;

  if (isNaN(val) || val <= 0) {
    showToast('El intervalo debe ser un número entero mayor a 0', 'error');
    return;
  }

  try {
    const res = await fetch(`/api/scheduler/tasks/${taskId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval_minutes: val })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Intervalo actualizado: ${data.message}`, 'success');
      await loadScheduledTasks();
    } else {
      throw new Error(data.detail || 'Fallo al actualizar intervalo');
    }
  } catch (err) {
    console.error(err);
    showToast(`Error al guardar: ${err.message}`, 'error');
  }
}

/**
 * Dispara inmediatamente la ejecución manual de una tarea programada sin esperar al temporizador.
 */
async function executeScheduledTaskNow(taskId) {
  const btn = document.getElementById(`btn-run-task-${taskId}`);
  const spinner = btn ? btn.querySelector('.loader-spinner') : null;
  const icon = btn ? btn.querySelector('.btn-icon') : null;

  try {
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';
    if (icon) icon.style.display = 'none';

    showToast(`Ejecutando tarea programada ${taskId}...`, 'info');

    const res = await fetch(`/api/scheduler/tasks/${taskId}/execute`, {
      method: 'POST'
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Tarea ejecutada con éxito. Archivo: ${data.result.saved_file}`, 'success');
      await loadScheduledTasks();
      await loadRawFiles();
      await updateKpis();
    } else {
      const errMsg = (data.result && data.result.error) || data.detail || 'Error en la tarea';
      showToast(`Fallo en la tarea: ${errMsg}`, 'error');
      await loadScheduledTasks();
    }
  } catch (err) {
    console.error(err);
    showToast(`Error de red: ${err.message}`, 'error');
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.style.display = 'none';
    if (icon) icon.style.display = 'inline-block';
  }
}

/**
 * Abre el modal con el contenido en bruto de tasks.yaml.
 */
async function openYamlModal() {
  const modal = document.getElementById('yaml-viewer-modal');
  const viewer = document.getElementById('yaml-content-viewer');

  if (modal) modal.style.display = 'flex';
  if (viewer) viewer.textContent = 'Leyendo config/tasks.yaml...';

  try {
    const res = await fetch('/api/scheduler/config-yaml');
    const data = await res.json();
    if (res.ok && viewer) {
      viewer.textContent = data.content || '# Archivo tasks.yaml vacío';
    }
  } catch (err) {
    if (viewer) viewer.textContent = `Error al consultar tasks.yaml: ${err.message}`;
  }
}

/**
 * Copia el contenido de tasks.yaml al portapapeles.
 */
function copyYamlContent() {
  const content = document.getElementById('yaml-content-viewer')?.textContent;
  if (content) {
    navigator.clipboard.writeText(content).then(() => {
      showToast('Configuración YAML copiada al portapapeles', 'success');
    }).catch(() => {
      showToast('Error al copiar contenido', 'error');
    });
  }
}

/* ==========================================================================
   5. GESTIÓN Y REPOSITORIO DE ARCHIVOS BRUTOS (data/raw/)
   ========================================================================== */

/**
 * Recarga la lista de archivos desde la API y refresca la tabla HTML con iconos limpios.
 */
async function loadRawFiles() {
  const tbody = document.getElementById('raw-files-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/raw-files');
    const data = await res.json();

    if (res.ok && data.files) {
      if (data.files.length === 0) {
        tbody.innerHTML = `
          <tr id="no-files-row">
            <td colspan="6" class="empty-table-cell">
              <div class="empty-state">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>No se registran archivos brutos en el directorio local <code>data/raw/</code>.</p>
                <p class="empty-hint">Ejecute cualquier conector activo para persistir la primera respuesta del servidor.</p>
              </div>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = data.files.map((f) => `
        <tr data-source="${f.source_id}" data-name="${f.filename}">
          <td>
            <span class="badge badge-source-${f.source_id}">${f.source_name}</span>
          </td>
          <td>
            <span class="font-mono file-name-highlight">${f.filename}</span>
          </td>
          <td class="font-mono">${f.size_formatted}</td>
          <td class="font-mono">${f.created_at}</td>
          <td><span class="ext-badge">${f.extension.toUpperCase()}</span></td>
          <td class="text-right table-actions">
            <button class="btn-icon-action btn-view" title="Inspeccionar contenido" onclick="viewFileContent('${f.filename}')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <span>Ver</span>
            </button>
            <a href="/api/raw-files/${f.filename}/download" class="btn-icon-action btn-download" title="Descargar archivo físico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              <span>Descargar</span>
            </a>
            <button class="btn-icon-action btn-delete" title="Eliminar registro local" onclick="deleteFile('${f.filename}')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </td>
        </tr>
      `).join('');

      filterFiles();
    }
  } catch (err) {
    console.error('Error al cargar archivos:', err);
  }
}

/**
 * Abre el modal para ver el contenido completo de un archivo bruto.
 */
async function viewFileContent(filename) {
  const modal = document.getElementById('file-viewer-modal');
  const modalName = document.getElementById('modal-file-name');
  const modalType = document.getElementById('modal-file-type');
  const modalMeta = document.getElementById('modal-file-meta');
  const modalContent = document.getElementById('modal-file-content');

  modal.style.display = 'flex';
  modalName.textContent = filename;
  modalContent.textContent = 'Cargando contenido del archivo...';

  try {
    const res = await fetch(`/api/raw-files/${encodeURIComponent(filename)}`);
    const data = await res.json();

    if (res.ok) {
      modalType.textContent = data.is_json ? 'JSON' : 'TEXTO / CSV';
      modalMeta.textContent = `${data.size_formatted} • ${data.lines_count} líneas`;

      if (data.is_json) {
        modalContent.textContent = JSON.stringify(data.content, null, 2);
      } else {
        modalContent.textContent = data.raw_text;
      }
    } else {
      modalContent.textContent = `Error al cargar archivo: ${data.detail || 'Desconocido'}`;
    }
  } catch (err) {
    modalContent.textContent = `Error de conexión: ${err.message}`;
  }
}

/**
 * Elimina un archivo de data/raw tras confirmación.
 */
async function deleteFile(filename) {
  if (!confirm(`¿Confirma la eliminación permanente del archivo "${filename}"?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/raw-files/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Archivo "${filename}" eliminado de disco`, 'info');
      await loadRawFiles();
      await updateKpis();
    } else {
      showToast(`Error: ${data.detail || 'No se pudo eliminar'}`, 'error');
    }
  } catch (err) {
    showToast(`Error al eliminar: ${err.message}`, 'error');
  }
}

/**
 * Filtra los archivos de la tabla en tiempo real por búsqueda y origen.
 */
function filterFiles() {
  const search = (document.getElementById('file-search')?.value || '').toLowerCase();
  const filterSource = document.getElementById('source-filter')?.value || 'ALL';
  const rows = document.querySelectorAll('#raw-files-tbody tr[data-name]');

  rows.forEach((row) => {
    const name = (row.getAttribute('data-name') || '').toLowerCase();
    const source = row.getAttribute('data-source') || '';

    const matchesSearch = name.includes(search);
    const matchesSource = (filterSource === 'ALL') || (source === filterSource);

    if (matchesSearch && matchesSource) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

/**
 * Copia el contenido mostrado en el modal al portapapeles.
 */
function copyModalContent() {
  const content = document.getElementById('modal-file-content')?.textContent;
  if (content) {
    navigator.clipboard.writeText(content).then(() => {
      showToast('Contenido copiado al portapapeles', 'success');
    }).catch(() => {
      showToast('Error al copiar contenido', 'error');
    });
  }
}

/* ==========================================================================
   6. MODALES Y KPIS
   ========================================================================== */

function openGuideModal() {
  const modal = document.getElementById('guide-modal');
  if (modal) modal.style.display = 'flex';
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'none';
}

function closeAllModals() {
  const modals = document.querySelectorAll('.modal-overlay');
  modals.forEach((m) => (m.style.display = 'none'));
}

/**
 * Consulta las estadísticas globales y actualiza los KPIs superiores.
 */
async function updateKpis() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (res.ok) {
      const activeEl = document.getElementById('kpi-active-sources');
      const filesEl = document.getElementById('kpi-total-files');
      const sizeEl = document.getElementById('kpi-total-size');

      if (activeEl) activeEl.textContent = `${data.active_sources} / ${data.total_sources}`;
      if (filesEl) filesEl.textContent = data.total_raw_files;
      if (sizeEl) sizeEl.textContent = data.total_size_formatted;
    }
  } catch (err) {
    console.error('Error al actualizar KPIs:', err);
  }
}

/* ==========================================================================
   7. NOTIFICACIONES TOAST (CORPORATIVAS CON ICONOS SVG)
   ========================================================================== */

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let iconSvg = '';
  if (type === 'success') {
    iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  } else if (type === 'error') {
    iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
  } else {
    iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
  }

  toast.innerHTML = `
    ${iconSvg}
    <span class="toast-message">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 200);
  }, 3500);
}
