import { apiService } from './apiService.js';

document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('toggleBtn');
    const createFormContainer = document.getElementById('createFormContainer');
    const createUserForm = document.getElementById('createUserForm');
    const workerRoleSelect = document.getElementById('workerRole');
    const roleDescBox = document.getElementById('roleDescBox');
    const errorContainer = document.getElementById('adminErrorContainer');

    let companyUsers = [];

    const descriptions = {
        MANAGER: [
            "Acceso a la curva de demanda predicha a 24h",
            "Precios marginales OMIE",
            "Herramientas de ajuste para la mesa de contratación"
        ],
        OPERATOR: [
            "Supervisión de curvas horarias",
            "Filtros territoriales por CCAA",
            "Gestión de alertas tempranas"
        ],
        ANALYST: [
            "Acceso al histórico de desviaciones",
            "Cálculo de sobrecostes estimados en euros (€)",
            "Generación de informes de auditoría"
        ],
        ADMIN: [
            "Control total corporativo",
            "Gestión de personal y altas",
            "Visibilidad global de la plataforma"
        ]
    };

    const roleTooltips = {
        'ADMIN': 'Administrador: Control total corporativo, gestión de personal, altas, modificaciones y visibilidad global.',
        'ANALYST': 'Analista / Auditor: Acceso a métricas de ML, histórico de desviaciones y cálculo de sobrecostes en €.',
        'OPERATOR': 'Operador de Red: Supervisión de curvas horarias, filtros territoriales y gestión de alertas tempranas.',
        'MANAGER': 'Gestor de Compra: Enfoque financiero, acceso a curva predicha 24h y precios OMIE.'
    };

    // Toggle para desplegar / ocultar el formulario de alta
    if (toggleBtn && createFormContainer) {
        toggleBtn.addEventListener('click', () => {
            createFormContainer.classList.toggle('show');
            if (createFormContainer.classList.contains('show')) {
                toggleBtn.innerHTML = '<i data-lucide="x" style="width: 16px; height: 16px;"></i> Cancelar';
            } else {
                toggleBtn.innerHTML = '<i data-lucide="user-plus" style="width: 16px; height: 16px;"></i> Nuevo Trabajador';
            }
            lucide.createIcons();
        });
    }

    // Actualizar descripción dinámica del rol en el formulario
    if (workerRoleSelect) {
        workerRoleSelect.addEventListener('change', () => {
            const selectedVal = workerRoleSelect.value;
            if (!selectedVal || !descriptions[selectedVal]) {
                roleDescBox.textContent = "Selecciona un rol para ver el detalle de los accesos asociados en la plataforma.";
                return;
            }
            const items = descriptions[selectedVal];
            let htmlList = '<ul style="margin: 0; padding-left: 20px; line-height: 1.5;">';
            items.forEach(item => { htmlList += `<li>${item}</li>`; });
            htmlList += '</ul>';
            roleDescBox.innerHTML = htmlList;
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

            companyUsers = users.map(user => ({
                id: user.id,
                name: user.nombre || '',
                email: user.email || '',
                role: (user.rol || '').toUpperCase(),
                cif: user.cif ?? 'Sin datos',       
                estado: user.estado ?? 'Sin datos', // <-- Añadimos el estado real
                date: user.fechaAlta ? new Date(user.fechaAlta).toLocaleDateString('es-ES') : '—'
            }));

            renderUsersTable();
        } catch (error) {
            console.error('Error al cargar los usuarios:', error);
            showError(`No se pudieron cargar los usuarios: ${error.message}`);
        }
    }

    // Renderizar la tabla de usuarios
    function renderUsersTable() {
        const tbody = document.getElementById('usersTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (companyUsers.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No hay usuarios registrados o sin conexión con la API.</td></tr>`;
            return;
        }

        const roleClasses = {
            'ADMIN': 'role-admin',
            'ANALYST': 'role-analyst',
            'OPERATOR': 'role-operator',
            'MANAGER': 'role-manager'
        };

        const roleLabels = {
            'ADMIN': 'Administrador',
            'ANALYST': 'Analista / Auditor',
            'OPERATOR': 'Operador de Red',
            'MANAGER': 'Gestor de Compra'
        };

        companyUsers.forEach(user => {
            const tr = document.createElement('tr');
            const tooltipText = roleTooltips[user.role] || 'Permisos asociados al rol.';
            
            tr.innerHTML = `
                <td><strong>${user.name}</strong><br><span style="font-size: 0.8rem; color: var(--text-muted);">${user.email}</span></td>
                <td>${user.cif}</td>
                <td><span class="badge-role ${roleClasses[user.role] || 'role-analyst'}" title="${tooltipText}">${roleLabels[user.role] || user.role}</span></td>
                <td>${user.date}</td>
                <td style="text-align: center;">
                    <button class="btn-icon edit-btn" data-id="${user.id}" title="Modificar"><i data-lucide="pencil" style="width: 16px; height: 16px;"></i></button>
                    <button class="btn-icon btn-delete delete-btn" data-id="${user.id}" title="Eliminar"><i data-lucide="trash-2" style="width: 16px; height: 16px;"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Enlazar eventos de edición y borrado dinámicamente
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => handleEditUser(btn.getAttribute('data-id')));
        });
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => handleDeleteUser(btn.getAttribute('data-id')));
        });

        lucide.createIcons();
    }

    // Manejar Alta de Usuario (POST /users)
    if (createUserForm) {
        createUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearError();

            const payload = {
                nombre: document.getElementById('workerName').value.trim(),
                email: document.getElementById('workerEmail').value.trim(),
                cif: document.getElementById('workerCIF').value.trim(),
                password: document.getElementById('workerPassword').value,
                rol: document.getElementById('workerRole').value
            };

            try {
                await apiService.createUser(payload);
                createUserForm.reset();
                roleDescBox.textContent = "Selecciona un rol para ver el detalle de los accesos asociados en la plataforma.";
                createFormContainer.classList.remove('show');
                toggleBtn.innerHTML = '<i data-lucide="user-plus" style="width: 16px; height: 16px;"></i> Nuevo Trabajador';
                
                // Recargar tabla con datos confirmados por la API
                await loadUsers();
            } catch (error) {
                console.error('Error al registrar usuario:', error);
                showError(`Error al registrar el usuario: ${error.message}`);
            }
        });
    }

    // Manejar Edición de Usuario (PUT /users/{id})
    async function handleEditUser(id) {
        const user = companyUsers.find(u => String(u.id) === String(id));
        if (!user) return;

        const newName = prompt("Modificar nombre completo:", user.name);
        if (newName === null) return;

        const newEmail = prompt("Modificar correo electrónico corporativo:", user.email);
        if (newEmail === null) return;

        const newRole = prompt("Modificar rol (ADMIN, MANAGER, OPERATOR, ANALYST):", user.role);
        if (newRole === null) return;

        const upperRole = newRole.toUpperCase();
        if (!['ADMIN', 'MANAGER', 'OPERATOR', 'ANALYST'].includes(upperRole)) {
            alert("Rol no válido. Debe ser ADMIN, MANAGER, OPERATOR o ANALYST.");
            return;
        }

        const updatePayload = {
            nombre: newName.trim(),
            email: newEmail.trim(),
            rol: upperRole
        };

        try {
            clearError();
            await apiService.updateUser(id, updatePayload);
            await loadUsers(); // Refrescar desde la API
        } catch (error) {
            console.error('Error al actualizar usuario:', error);
            showError(`No se pudo actualizar el usuario: ${error.message}`);
        }
    }

    // Manejar Eliminación de Usuario (DELETE /users/{id})
    async function handleDeleteUser(id) {
        if (!confirm("¿Estás seguro de que deseas eliminar este usuario del CIF corporativo?")) return;

        try {
            clearError();
            await apiService.deleteUser(id);
            await loadUsers(); // Refrescar la tabla tras el éxito
        } catch (error) {
            console.error('Error al eliminar usuario:', error);
            showError(`No se pudo eliminar el usuario: ${error.message}`);
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

    // Arranque inicial
    loadUsers();
    lucide.createIcons();
});