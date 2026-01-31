/**
 * Helper para incluir CSRF token en peticiones AJAX/fetch
 */

// Obtener token CSRF del meta tag
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Configurar fetch para incluir CSRF automáticamente
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    // Solo agregar CSRF si es POST/PUT/DELETE y no es una API externa
    if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            // Es una petición interna
            if (!options.headers) {
                options.headers = {};
            }
            if (typeof options.headers === 'object' && !(options.headers instanceof Headers)) {
                options.headers['X-CSRFToken'] = getCSRFToken();
            } else if (options.headers instanceof Headers) {
                options.headers.set('X-CSRFToken', getCSRFToken());
            }
        }
    }
    return originalFetch.call(this, url, options);
};

// Helper para jQuery (si se usa)
if (typeof jQuery !== 'undefined') {
    jQuery.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
            }
        }
    });
}





