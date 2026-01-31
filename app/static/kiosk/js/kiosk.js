/**
 * JavaScript para Bimba Kiosk
 * Funciones comunes y utilidades
 */

// Prevenir zoom accidental en dispositivos táctiles
document.addEventListener('touchstart', function(event) {
    if (event.touches.length > 1) {
        event.preventDefault();
    }
}, { passive: false });

let lastTouchEnd = 0;
document.addEventListener('touchend', function(event) {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
        event.preventDefault();
    }
    lastTouchEnd = now;
}, false);

// Prevenir doble tap zoom
document.addEventListener('dblclick', function(event) {
    event.preventDefault();
}, false);

// Utilidad para formatear números como moneda
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency: 'CLP',
        minimumFractionDigits: 0
    }).format(amount);
}

// Utilidad para hacer requests con manejo de errores
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Auto-redirección después de inactividad (opcional)
let inactivityTimer;
const INACTIVITY_TIMEOUT = 300000; // 5 minutos

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(() => {
        // Solo redirigir si estamos en la pantalla de inicio o productos
        const currentPath = window.location.pathname;
        if (currentPath === '/kiosk' || currentPath === '/kiosk/products') {
            window.location.href = '/kiosk';
        }
    }, INACTIVITY_TIMEOUT);
}

// Resetear timer en interacciones
['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
    document.addEventListener(event, resetInactivityTimer, true);
});

// Inicializar timer al cargar
resetInactivityTimer();






