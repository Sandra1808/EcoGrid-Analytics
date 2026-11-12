const API_BASE_URL = 'http://localhost:8080/api';

export const apiService = {
    /**
     * Obtenemos el listado de comunidades autónomas disponibles.
     */
    async getComunidades() {
        const response = await fetch(`${API_BASE_URL}/comunidades`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los datos de las comunidades autónomas`);
        }
        return await response.json();
    },

    /**
     * Obtenemos el resumen global del dashboard para una fecha concreta.
     * @param {string} fecha Fecha en formato YYYY-MM-DD
     */
    async getDashboardSummary(fecha, ccaaId = '10') {
        const params = new URLSearchParams({ fecha, ccaaId });
        const response = await fetch(`${API_BASE_URL}/dashboard/summary?${params}`);

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener el resumen`);
        }

        return response.json();
    },


    /**
     * Obtenemos la serie de demanda horaria filtrada por CCAA y rango de fechas (ISO).
     */
    async getDemandSeries(fecha, ccaaId = '10') {
        const params = new URLSearchParams({ fecha, ccaaId });
        const response = await fetch(`${API_BASE_URL}/demand/series?${params}`);

        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo obtener la serie`);
        }

        return response.json();
    },

    /**
     * Obtenemos las alertas operativas del sistema.
     */
    async getAlerts() {
        const response = await fetch(`${API_BASE_URL}/alerts`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudieron obtener las alertas del sistema`);
        }
        return await response.json();
    },

    /**
     * Obtenemos las fuentes de datos configuradas.
     */
    async getSources() {
        const response = await fetch(`${API_BASE_URL}/sources`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudieron obtener las fuentes de datos`);
        }
        return await response.json();
    },

    /**
     * Obtenemos los ficheros en bruto (raw files) ingestados.
     */
    async getRawFiles() {
        const response = await fetch(`${API_BASE_URL}/raw-files`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los ficheros raw`);
        }
        return await response.json();
    },

    /**
     * Obtenemos las tareas programadas (scheduler).
     */
    async getSchedulerTasks() {
        const response = await fetch(`${API_BASE_URL}/scheduler/tasks`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener las tareas programadas`);
        }
        return await response.json();
    },

    /**
     * Re-ejecuta el modelo de predicción de IA.
     */
    async triggerPrediction() {
        const response = await fetch(`${API_BASE_URL}/prediction/run`, { // Ajusta la ruta "/prediction/run" si tu endpoint de Spring Boot es diferente
            method: 'POST'
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
        const response = await fetch(`${API_BASE_URL}/users`);
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido obtener los datos de los usuarios`);
        }
        return await response.json();
    },

    async createUser(userData) {
        const response = await fetch(`${API_BASE_URL}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se han podido registrar los datos del usuario`);
        }
        // Algunos backends devuelven JSON y otros vacío (204/201)
        const text = await response.text();
        return text ? JSON.parse(text) : {};
    },

    async updateUser(id, userData) {
        const response = await fetch(`${API_BASE_URL}/users/${id}`, {
            method: 'PUT',
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
            method: 'DELETE'
        });
        if (!response.ok) {
            throw new Error(`Error HTTP ${response.status}: No se pudo eliminar el usuario`);
        }
        return true;
    }
};