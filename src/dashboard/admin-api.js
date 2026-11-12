import { apiService } from './apiService.js';

document.addEventListener('DOMContentLoaded', async () => {
    const errorContainer = document.getElementById('adminErrorContainer');

    let usuario;
    try {
        usuario = await apiService.getCurrentUser();
    } catch (error) {
        window.location.replace('index.html');
        return;
    }

    const rol = (usuario.rol || '').toUpperCase();
    if (rol !== 'ADMIN' && rol !== 'ADMINISTRADOR') {
        window.location.replace('dashboard.html');
        return;
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

    // Cargar usuarios desde la API utilizando apiService
    async function loadUsers() {
        try {
            clearError();
            const users = await apiService.getUsers();

            if (!Array.isArray(users)) {
                throw new Error('La respuesta del servidor no tiene un formato de lista válido');
            }

            renderUsersTable(users);
        } catch (error) {
            console.error('Error al cargar los usuarios:', error);
            showError(`No se pudieron cargar los usuarios: ${error.message}`);
        }
    }

    // Renderizar la tabla de usuarios
    function renderUsersTable(users) {
        const tbody = document.getElementById('usersTableBody');
        if (!tbody) return;

        tbody.replaceChildren();

        if (users.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 4;
            cell.style.textAlign = 'center';
            cell.style.color = 'var(--text-muted)';
            cell.textContent = 'No hay usuarios registrados.';
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }

        const roleClasses = {
            ADMIN: 'role-admin',
            ANALYST: 'role-analyst',
            OPERATOR: 'role-operator',
            MANAGER: 'role-manager'
        };

        const roleLabels = {
            ADMIN: 'Administrador',
            ANALYST: 'Analista / Auditor',
            OPERATOR: 'Operador de Red',
            MANAGER: 'Gestor de Compra'
        };

        const roleTooltips = {
            ADMIN: 'Administrador: acceso de administración.',
            ANALYST: 'Analista / Auditor: acceso a métricas e histórico.',
            OPERATOR: 'Operador de Red: supervisión de curvas y alertas.',
            MANAGER: 'Gestor de Compra: acceso a información financiera.'
        };

        users.forEach(user => {
            const role = (user.rol || '').toUpperCase();
            const row = document.createElement('tr');

            const nameCell = document.createElement('td');
            const name = document.createElement('strong');
            name.textContent = user.nombre || '';
            nameCell.appendChild(name);

            const email = document.createElement('span');
            email.style.fontSize = '0.8rem';
            email.style.color = 'var(--text-muted)';
            email.textContent = user.email || '';
            nameCell.appendChild(document.createElement('br'));
            nameCell.appendChild(email);

            const cifCell = document.createElement('td');
            cifCell.textContent = user.cif || 'Sin datos';

            const roleCell = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = `badge-role ${roleClasses[role] || 'role-analyst'}`;
            badge.title = roleTooltips[role] || 'Permisos asociados al rol.';
            badge.textContent = roleLabels[role] || role || 'Sin rol';
            roleCell.appendChild(badge);

            const dateCell = document.createElement('td');
            dateCell.textContent = user.fechaAlta
                ? new Date(user.fechaAlta).toLocaleDateString('es-ES')
                : '—';

            row.append(nameCell, cifCell, roleCell, dateCell);
            tbody.appendChild(row);
        });

        lucide.createIcons();
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

    // Arranque inicial
    await loadUsers();
    lucide.createIcons();
});