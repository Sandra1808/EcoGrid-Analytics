/**
 * Módulo de control de acceso y gestión de permisos corporativos
 * Adapta la visibilidad del panel analítico según el rol autenticado
 */

document.addEventListener('DOMContentLoaded', () => {
    verifySessionAccess();
});

function verifySessionAccess() {
    const currentPath = window.location.pathname;
    const isLoginScreen = currentPath.includes('index.html') || currentPath.endsWith('/');

    // ==========================================
    // MODO DESARROLLO (FORZAR ROL PARA PRUEBAS)
    // Cambia esto a 'ADMIN', 'ANALYST', 'OPERATOR' o 'MANAGER' 
    // para probar cada vista al recargar la página.
    // ==========================================
    const rolParaPruebas = 'MANAGER'; // Cambia temporalmente este valor para probar

    if (!isLoginScreen) {
        sessionStorage.setItem('authRole', rolParaPruebas);
        sessionStorage.setItem('authUser', `${rolParaPruebas.toLowerCase()}@ecogrid.com`);
    }

    const currentRole = sessionStorage.getItem('authRole');
    const currentUser = sessionStorage.getItem('authUser') || 'usuario@ecogrid.com';

    // Si no hay sesión activa y no estamos en el login, redirigir al acceso
    if (!currentRole && !isLoginScreen) {
        window.location.href = 'index.html';
        return;
    }

    // Si estamos dentro del panel principal, aplicar filtros visuales por rol
    if (!isLoginScreen && currentPath.includes('dashboard.html')) {
        enforceRolePermissions(currentRole, currentUser);
    }
}

function enforceRolePermissions(role, userEmail) {
    console.log(`Aplicando restricciones de visualización para el rol: ${role} (${userEmail})`);

    // Referencias a elementos del DOM
    const mlMetricsSection = document.getElementById('mlMetricsSection');      // Métricas de IA y curvas (Analista)
    const controlPanelSection = document.getElementById('controlPanelSection'); // Panel de filtros y control de curvas (Analista)
    const operationalAlerts = document.getElementById('operationalAlerts');  // Picos, alertas y puntos críticos (Operador)
    const financialSection = document.getElementById('financialSection');      // Impacto económico y costes en € (Gestor)
    const adminLink = document.getElementById('adminLink');                      // Enlace de administración
    const dashboardTitle = document.getElementById('dashboardTitle');            // Título principal del panel
    const userNameDisplay = document.getElementById('userNameDisplay');          // Etiqueta del nombre de usuario

    // Mostrar el correo/nombre del usuario junto a cerrar sesión (ya sin emojis a pelo)
    if (userNameDisplay) {
        userNameDisplay.innerHTML = `<i data-lucide="user" style="width: 14px; height: 14px; vertical-align: middle; margin-right: 4px;"></i> ${userEmail}`;
        lucide.createIcons();
    }

    // Nombres descriptivos para los roles en la cabecera
    const roleTitles = {
        'ADMIN': 'Panel Operativo - Administrador Empresa',
        'ANALYST': 'Panel Operativo - Analista de Datos / ML',
        'OPERATOR': 'Panel Operativo - Operador de Red',
        'MANAGER': 'Panel Operativo - Gestor de Compra'
    };

    if (dashboardTitle) {
        dashboardTitle.textContent = roleTitles[role] || 'EcoGrid Analytics - Panel Operativo';
    }

    // Por defecto, ocultamos el acceso de administración para todos salvo ADMIN
    if (adminLink) {
        adminLink.style.display = (role === 'ADMIN') ? 'inline' : 'none';
    }

    // Ajustar visibilidad de las secciones según las responsabilidades de la matriz corporativa
    switch (role) {
        case 'ANALYST':
            if (financialSection) financialSection.style.display = 'none';
            break;

        case 'OPERATOR':
            if (mlMetricsSection) mlMetricsSection.style.display = 'none';
            if (controlPanelSection) controlPanelSection.style.display = 'none';
            if (financialSection) financialSection.style.display = 'none';
            break;

        case 'MANAGER':
            if (mlMetricsSection) mlMetricsSection.style.display = 'none';
            if (controlPanelSection) controlPanelSection.style.display = 'none'; 
            if (operationalAlerts) operationalAlerts.style.display = 'none';
            break;

        case 'ADMIN':
            // El administrador tiene acceso a todas las secciones
            break;

        default:
            console.warn('Perfil de usuario no reconocido. Aplicando restricciones de seguridad por defecto.');
            break;
    }
}