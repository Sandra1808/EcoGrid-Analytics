const API_BASE_URL = 'http://localhost:8080/api';

export const apiService = {
  /**
   * Obtenemos el estado actual del dashboard, con los KPIs y la serie temporal de la demanda energértica
   * @param {string} fecha Fecha objetivo en formato YYYY-MM-DD.
   * @returns {Promise<Object>} Resumen del dashboard.
   */
  async getDashboardSummary(fecha = '2026-10-27') {
    try {
      const response = await fetch(
        `${API_BASE_URL}/dashboard/summary?fecha=${encodeURIComponent(fecha)}`
      );

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se ha podido obtener el estado del dashboard, se usarán datos simulados en este caso.', error);

      return {
        fecha_objetivo: fecha,
        ccaa: 'ES-VC',
        kpis: {
          demanda_media_mw: 3240,
          coste_desvio_estimado_eur: 18750,
          nivel_alerta_global: 'NORMAL',
        },
        serie_temporal: Array.from({ length: 24 }, (_, hora) => ({
          fecHora: `${fecha}T${String(hora).padStart(2, '0')}:00:00`,
          demanda_mw: 3000 + (hora % 6) * 100,
        })),
      };
    }
  },

  /**
   * Cogemos la serie de demanda para el día indicado.
   * @param {string} fecha Formato de la fecha YYYY-MM-DD
   * @returns {Promise<Array<Object>>} Serie horaria de demanda.
   */
  async getDemandSeries(fecha = '2026-10-27') {
    try {
      const response = await fetch(
        `${API_BASE_URL}/demand/series?fecha=${encodeURIComponent(fecha)}`
      );

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se han podido obtener la serie de demanda solicitada, se usarán datos simulados en este caso.', error);

      return Array.from({ length: 24 }, (_, hora) => {
        const demandaRealMWH = 3000 + (hora % 6) * 100;
        const demandaPredichaMWH = demandaRealMWH + (hora % 3) * 20;

        return {
          fecHora: `${fecha}T${String(hora).padStart(2, '0')}:00:00`,
          demandaRealMWH,
          demandaPredichaMWH,
          desviacionMWH: demandaRealMWH - demandaPredichaMWH,
        };
      });
    }
  },

  /**
   * Cogemos las alertas que se han generado en el sistema
   * @returns {Promise<Array<Object>>}
   */
  async getAlerts() {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts`);

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se han podido obtener las alertas progrmadas, se usarán datos simulados en este caso.', error);

      return [
        {
          id: 1,
          fecHora: '2026-10-27T18:00:00',
          tipo: 'desviacion_demanda',
          mensaje: 'Desviación de demanda superior al umbral previsto.',
          nivelAlerta: 'ALTO',
        },
        {
          id: 2,
          fecHora: '2026-10-27T12:00:00',
          tipo: 'operacion',
          mensaje: 'Operación del sistema dentro de los parámetros normales.',
          nivelAlerta: 'NORMAL',
        },
      ];
    }
  },

  /**
   * Obtenemos las fuentes de datos que están disponibles
   * @returns {Promise<Array<Object>>} Fuentes y estado de disponibilidad.
   */
  async getSources() {
    try {
      const response = await fetch(`${API_BASE_URL}/sources`);

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se pudieron obtener las fuentes; se usarán datos simulados.', error);

      return ['OMIE', 'REE', 'Open-Meteo'].map((nombre) => ({
        nombre,
        estado: 'disponible',
      }));
    }
  },

  /**
   * Obtenemos los ficheros en crudo que se han subido 
   * @returns {Promise<Array<Object>>} Lista de ficheros raw.
   */
  async getRawFiles() {
    try {
      const response = await fetch(`${API_BASE_URL}/raw-files`);

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se pudieron obtener los ficheros; se usarán datos simulados.', error);

      return [
        {
          nombre: 'dataset_maestro_ecogrid.csv',
          peso: '2.4 MB',
          fecha_ingesta: '2026-10-27T06:00:00',
        },
        {
          nombre: 'prediccion_demanda_2026-10-27.csv',
          peso: '184 KB',
          fecha_ingesta: '2026-10-27T06:15:00',
        },
      ];
    }
  },

  /**
   * Obtenemos los usuarios registrados en la base de datos
   * @returns {Promise<Array<Object>>} Lista de usuarios.
   */
  async getUsers() {
    try {
      const response = await fetch(`${API_BASE_URL}/users`);

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se han podido obtener los usuarios, se usarán datos simulados en este caso.', error);

      return [
        {
          id: 1,
          nombre: 'Sandra Martínez',
          email: 'sandra.martinez@example.com',
          rol: 'admin',
          estado: 'activo',
        },
        {
          id: 2,
          nombre: 'Carlos Ruiz',
          email: 'carlos.ruiz@example.com',
          rol: 'analista',
          estado: 'activo',
        },
      ];
    }
  },

  /**
   * Obtiene las tareas que hay programadas en el backend para que se ejecuten automaticamente
   * @returns {Promise<Array<Object>>} Lista de tareas programadas.
   */
  async getSchedulerTasks() {
    try {
      const response = await fetch(`${API_BASE_URL}/scheduler/tasks`);

      if (![200, 201].includes(response.status)) {
        throw new Error(`Estado HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('No se han podido obtener las tareas programadas, se usarán datos simulados en este caso.', error);

      return [
        {
          nombre: 'ingesta_omie',
          estado: 'completada',
          ultima_ejecucion: '2026-10-27T06:00:00',
        },
        {
          nombre: 'prediccion_diaria',
          estado: 'pendiente',
          ultima_ejecucion: '2026-10-27T06:30:00',
        },
      ];
    }
  },
};