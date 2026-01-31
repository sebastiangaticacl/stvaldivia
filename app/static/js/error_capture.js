/**
 * Error Capture Mode - Captura sistemática de errores para auditoría
 * Solo activo en desarrollo o cuando DEBUG_ERRORS=1
 */

(function() {
    'use strict';

    // Configuración
    const DEBUG_ERRORS = window.DEBUG_ERRORS || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    
    if (!DEBUG_ERRORS) {
        return; // No capturar en producción por defecto
    }

    // Almacenamiento de errores
    const errorStore = {
        js_errors: [],
        network_errors: [],
        csp_violations: [],
        unhandled_rejections: [],
        metadata: {
            start_time: new Date().toISOString(),
            user_agent: navigator.userAgent,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            url: window.location.href,
            pathname: window.location.pathname
        }
    };

    // Helper para agregar timestamp y contexto
    function enrichError(error) {
        return {
            ...error,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            pathname: window.location.pathname,
            user_agent: navigator.userAgent,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };
    }

    // 1. Capturar errores JavaScript
    window.addEventListener('error', function(event) {
        const error = enrichError({
            type: 'js_error',
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error ? event.error.stack : null,
            error_name: event.error ? event.error.name : null
        });
        
        errorStore.js_errors.push(error);
        
        // Agrupar en consola
        console.groupCollapsed(`🔴 JS Error: ${event.message}`);
        console.error('File:', event.filename, `(${event.lineno}:${event.colno})`);
        if (event.error && event.error.stack) {
            console.error('Stack:', event.error.stack);
        }
        console.groupEnd();
    }, true);

    // 2. Capturar promesas rechazadas sin manejar
    window.addEventListener('unhandledrejection', function(event) {
        const error = enrichError({
            type: 'unhandled_rejection',
            reason: event.reason ? String(event.reason) : 'Unknown',
            stack: event.reason && event.reason.stack ? event.reason.stack : null
        });
        
        errorStore.unhandled_rejections.push(error);
        
        console.groupCollapsed(`🔴 Unhandled Rejection: ${error.reason}`);
        if (error.stack) {
            console.error('Stack:', error.stack);
        }
        console.groupEnd();
    });

    // 3. Capturar violaciones CSP (si están disponibles)
    if (window.SecurityPolicyViolationEvent) {
        document.addEventListener('securitypolicyviolation', function(event) {
            const violation = enrichError({
                type: 'csp_violation',
                violated_directive: event.violatedDirective,
                effective_directive: event.effectiveDirective,
                blocked_uri: event.blockedURI,
                document_uri: event.documentURI,
                source_file: event.sourceFile,
                line_number: event.lineNumber,
                column_number: event.columnNumber
            });
            
            errorStore.csp_violations.push(violation);
            
            console.groupCollapsed(`🔴 CSP Violation: ${violation.violated_directive}`);
            console.error('Blocked URI:', violation.blocked_uri);
            console.error('Source:', violation.source_file, `(${violation.line_number}:${violation.column_number})`);
            console.groupEnd();
        });
    }

    // 4. Interceptar fetch
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = typeof args[0] === 'string' ? args[0] : args[0].url;
        const method = args[1] && args[1].method ? args[1].method : 'GET';
        const startTime = performance.now();
        
        return originalFetch.apply(this, args)
            .then(response => {
                const duration = performance.now() - startTime;
                
                // Capturar errores 4xx/5xx
                if (response.status >= 400) {
                    const error = enrichError({
                        type: 'network_error',
                        method: method,
                        url: url,
                        status: response.status,
                        status_text: response.statusText,
                        duration_ms: Math.round(duration),
                        headers: Object.fromEntries(response.headers.entries())
                    });
                    
                    // Intentar leer body si es JSON
                    response.clone().json()
                        .then(body => {
                            error.body = body;
                            errorStore.network_errors.push(error);
                        })
                        .catch(() => {
                            // Si no es JSON, leer como text
                            response.clone().text()
                                .then(text => {
                                    error.body_text = text.substring(0, 500); // Limitar tamaño
                                    errorStore.network_errors.push(error);
                                })
                                .catch(() => {
                                    errorStore.network_errors.push(error);
                                });
                        });
                    
                    console.groupCollapsed(`🔴 Network Error: ${method} ${url} → ${response.status}`);
                    console.error('Status:', response.status, response.statusText);
                    console.error('Duration:', Math.round(duration), 'ms');
                    console.groupEnd();
                }
                
                return response;
            })
            .catch(error => {
                const duration = performance.now() - startTime;
                const networkError = enrichError({
                    type: 'network_error',
                    method: method,
                    url: url,
                    status: 0,
                    status_text: 'Network Error',
                    duration_ms: Math.round(duration),
                    error_message: error.message
                });
                
                errorStore.network_errors.push(networkError);
                
                console.groupCollapsed(`🔴 Network Error: ${method} ${url} → Network Error`);
                console.error('Error:', error.message);
                console.groupEnd();
                
                throw error;
            });
    };

    // 5. Interceptar XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._errorCaptureMethod = method;
        this._errorCaptureUrl = url;
        this._errorCaptureStartTime = performance.now();
        return originalXHROpen.apply(this, [method, url, ...rest]);
    };
    
    XMLHttpRequest.prototype.send = function(...args) {
        const xhr = this;
        const method = xhr._errorCaptureMethod;
        const url = xhr._errorCaptureUrl;
        const startTime = xhr._errorCaptureStartTime;
        
        xhr.addEventListener('loadend', function() {
            const duration = performance.now() - startTime;
            
            if (xhr.status >= 400) {
                const error = enrichError({
                    type: 'network_error',
                    method: method,
                    url: url,
                    status: xhr.status,
                    status_text: xhr.statusText,
                    duration_ms: Math.round(duration),
                    response_text: xhr.responseText ? xhr.responseText.substring(0, 500) : null
                });
                
                errorStore.network_errors.push(error);
                
                console.groupCollapsed(`🔴 XHR Error: ${method} ${url} → ${xhr.status}`);
                console.error('Status:', xhr.status, xhr.statusText);
                console.error('Duration:', Math.round(duration), 'ms');
                console.groupEnd();
            }
        });
        
        return originalXHRSend.apply(this, args);
    };

    // 6. API para exportar errores
    window.getErrorReport = function() {
        return {
            ...errorStore,
            metadata: {
                ...errorStore.metadata,
                end_time: new Date().toISOString(),
                total_js_errors: errorStore.js_errors.length,
                total_network_errors: errorStore.network_errors.length,
                total_csp_violations: errorStore.csp_violations.length,
                total_unhandled_rejections: errorStore.unhandled_rejections.length
            }
        };
    };

    // 7. Limpiar errores
    window.clearErrorReport = function() {
        errorStore.js_errors = [];
        errorStore.network_errors = [];
        errorStore.csp_violations = [];
        errorStore.unhandled_rejections = [];
        errorStore.metadata.start_time = new Date().toISOString();
        errorStore.metadata.url = window.location.href;
        errorStore.metadata.pathname = window.location.pathname;
        console.log('✅ Error report cleared');
    };

    // 8. Log inicial
    console.log('✅ Error Capture Mode activado');
    console.log('Usa window.getErrorReport() para obtener el reporte');
    console.log('Usa window.clearErrorReport() para limpiar el reporte');

    // Exponer globalmente para debugging
    window.errorStore = errorStore;
})();


