/**
 * Utilidades para formateo de fechas y horas
 * Formato estándar: DD/MM/YYYY HH:MM (24 horas)
 */

/**
 * Formatea una fecha en formato DD/MM/YYYY HH:MM (24 horas)
 * @param {string|Date} dateString - Fecha como string ISO o objeto Date
 * @returns {string} Fecha formateada
 */
function formatFecha(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return dateString; // Retornar original si no se puede parsear
        }
        
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (e) {
        console.warn('Error formateando fecha:', e);
        return dateString;
    }
}

/**
 * Formatea una fecha en formato DD/MM/YYYY (sin hora)
 * @param {string|Date} dateString - Fecha como string ISO o objeto Date
 * @returns {string} Fecha formateada
 */
function formatFechaSolo(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        
        return `${day}/${month}/${year}`;
    } catch (e) {
        console.warn('Error formateando fecha:', e);
        return dateString;
    }
}

/**
 * Formatea una hora en formato HH:MM (24 horas)
 * @param {string|Date} dateString - Fecha como string ISO o objeto Date
 * @returns {string} Hora formateada
 */
function formatHora(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${hours}:${minutes}`;
    } catch (e) {
        console.warn('Error formateando hora:', e);
        return dateString;
    }
}

/**
 * Formatea una fecha/hora usando toLocaleString con formato chileno
 * @param {string|Date} dateString - Fecha como string ISO o objeto Date
 * @param {Object} options - Opciones adicionales para toLocaleString
 * @returns {string} Fecha formateada
 */
function formatFechaLocale(dateString, options = {}) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        const defaultOptions = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            ...options
        };
        
        return date.toLocaleString('es-CL', defaultOptions);
    } catch (e) {
        console.warn('Error formateando fecha con locale:', e);
        return dateString;
    }
}

// Exportar funciones para uso global
window.formatFecha = formatFecha;
window.formatFechaSolo = formatFechaSolo;
window.formatHora = formatHora;
window.formatFechaLocale = formatFechaLocale;

