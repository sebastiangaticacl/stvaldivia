/**
 * Utilidades para formateo de moneda chilena
 * Formato estándar: puntos como separador de miles, sin decimales
 */

/**
 * Formatea un número como moneda chilena
 * Puntos como separador de miles, sin decimales
 * @param {number|string} value - Valor numérico
 * @param {boolean} includeSymbol - Si incluir símbolo $ (default: false)
 * @returns {string} Valor formateado
 */
function formatCurrency(value, includeSymbol = false) {
    if (value === null || value === undefined || value === '') {
        return includeSymbol ? '$0' : '0';
    }
    
    try {
        // Convertir a número y redondear
        const num = Math.round(parseFloat(value));
        
        if (isNaN(num)) {
            return includeSymbol ? '$0' : '0';
        }
        
        // Formatear con puntos como separador de miles
        const formatted = num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        
        return includeSymbol ? `$${formatted}` : formatted;
    } catch (e) {
        console.warn('Error formateando moneda:', e);
        return includeSymbol ? '$0' : '0';
    }
}

/**
 * Formatea un número como moneda chilena con símbolo $
 * @param {number|string} value - Valor numérico
 * @returns {string} Valor formateado con símbolo
 */
function formatCurrencyWithSymbol(value) {
    return formatCurrency(value, true);
}

/**
 * Parsea un string de moneda formateado a número
 * @param {string} currencyString - String formateado (ej: "$1.234.567" o "1.234.567")
 * @returns {number} Valor numérico
 */
function parseCurrency(currencyString) {
    if (!currencyString) return 0;
    
    try {
        // Remover símbolos y puntos, luego convertir a número
        const cleaned = String(currencyString)
            .replace(/\$/g, '')
            .replace(/\./g, '')
            .replace(/,/g, '.')
            .trim();
        
        const num = parseFloat(cleaned);
        return isNaN(num) ? 0 : num;
    } catch (e) {
        console.warn('Error parseando moneda:', e);
        return 0;
    }
}

/**
 * Formatea un número usando toLocaleString con formato chileno
 * @param {number|string} value - Valor numérico
 * @param {Object} options - Opciones adicionales para toLocaleString
 * @returns {string} Valor formateado
 */
function formatNumberLocale(value, options = {}) {
    if (value === null || value === undefined || value === '') {
        return '0';
    }
    
    try {
        const num = parseFloat(value);
        
        if (isNaN(num)) {
            return '0';
        }
        
        const defaultOptions = {
            maximumFractionDigits: 0,
            ...options
        };
        
        return num.toLocaleString('es-CL', defaultOptions);
    } catch (e) {
        console.warn('Error formateando número con locale:', e);
        return '0';
    }
}

// Exportar funciones para uso global
window.formatCurrency = formatCurrency;
window.formatCurrencyWithSymbol = formatCurrencyWithSymbol;
window.parseCurrency = parseCurrency;
window.formatNumberLocale = formatNumberLocale;

