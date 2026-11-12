const API_BASE_URL = 'http://localhost:8080/api';

export const apiService = {
    async login(email, password) {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(`Error HTTP ${response.status}${detail ? `: ${detail}` : ''}`);
        }

        const text = await response.text();
        return text ? JSON.parse(text) : null;
    },

    async getCurrentUser() {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No hay una sesión activa`);
        }

        return response.json();
    },

    async getActiveModel() {
        const response = await fetch(`${API_BASE_URL}/models/active`, {
            credentials: 'include'
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(`Error HTTP ${response.status}${detail ? `: ${detail}` : ''}`);
        }

        return response.json();
    },

    async logout() {
        const response = await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo cerrar la sesión`);
        }
    },

    /**
     * Obtenemos el listado de comunidades autónomas disponibles.
     */
    async getComunidades() {
        const response = await fetch(`${API_BASE_URL}/comunidades`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los datos de las comunidades autónomas`);
        }

        return response.json();
    },

    /**
     * Obtenemos el resumen global del dashboard para una fecha concreta.
     * @param {string} fecha Fecha en formato YYYY-MM-DD
     */
    async getDashboardSummary(fecha, ccaaId = '1') {
        const params = new URLSearchParams({ fecha, ccaaId });
        const response = await fetch(`${API_BASE_URL}/dashboard/summary?${params}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener el resumen`);
        }

        return response.json();
    },

    /**
     * Obtenemos la serie de demanda horaria filtrada por CCAA y fecha.
     */
    async getDemandSeries(fecha, ccaaId = '1') {
        const params = new URLSearchParams({ fecha, ccaaId });
        const response = await fetch(`${API_BASE_URL}/demand/series?${params}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener la serie`);
        }

        return response.json();
    },

    /**
     * Obtenemos las alertas operativas del sistema.
     */
    async getAlerts() {
        const response = await fetch(`${API_BASE_URL}/alerts`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudieron obtener las alertas del sistema`);
        }

        return response.json();
    },

    /**
     * Obtenemos las fuentes de datos configuradas.
     */
    async getSources() {
        const response = await fetch(`${API_BASE_URL}/sources`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudieron obtener las fuentes de datos`);
        }

        return response.json();
    },

    /**
     * Obtenemos los ficheros en bruto (raw files) ingestados.
     */
    async getRawFiles() {
        const response = await fetch(`${API_BASE_URL}/raw-files`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los ficheros raw`);
        }

        return response.json();
    },

    /**
     * Obtenemos las tareas programadas (scheduler).
     */
    async getSchedulerTasks() {
        const response = await fetch(`${API_BASE_URL}/scheduler/tasks`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener las tareas programadas`);
        }

        return response.json();
    },

    /**
     * Re-ejecuta el modelo de predicción de IA.
     */
    async triggerPrediction() {
        const response = await fetch(`${API_BASE_URL}/prediction/run`, {
            method: 'POST',
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo re-ejecutar la predicción`);
        }

        const text = await response.text();
        return text ? JSON.parse(text) : {};
    },

    /**
     * OPERACIONES CRUD DE USUARIOS (Para admin.html)
     */

    async getUsers() {
        const response = await fetch(`${API_BASE_URL}/users`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los datos de los usuarios`);
        }

        return response.json();
    },

    async createUser(userData) {
        const response = await fetch(`${API_BASE_URL}/users`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido registrar los datos del usuario`);
        }

        const text = await response.text();
        return text ? JSON.parse(text) : {};
    },

    async updateUser(id, userData) {
        const response = await fetch(`${API_BASE_URL}/users/${id}`, {
            method: 'PUT',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo actualizar el usuario`);
        }

        const text = await response.text();
        return text ? JSON.parse(text) : {};
    },

    async deleteUser(id) {
        const response = await fetch(`${API_BASE_URL}/users/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo eliminar el usuario`);
        }

        return true;
    }
};