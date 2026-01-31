/**
 * Módulo de integración Getnet para Linux usando Web Serial API
 * 
 * Este módulo maneja la comunicación con el POS Getnet conectado por USB
 * desde el navegador Chromium en modo kiosko en Linux.
 * 
 * IMPORTANTE: Usa la librería oficial Getnet en modo "Comunicación vía Navegador"
 * (NO Serial Communication Server de Windows).
 */

// Importar la librería Getnet oficial
// NOTA: Asegúrate de tener getnet.min.js en /static/getnet/getnet.min.js
import Getnet from "../getnet/getnet.min.js";

/**
 * Estado interno del módulo
 */
const estado = {
    inicializado: false,
    puertoConectado: false,
    metaCaja: null,
    ticketNumber: 1,  // TODO: set ticketNumber secuencial desde backend o localStorage
    employeeId: 1,    // TODO: set employeeId real según configuración del tótem
    callbacks: {
        onVentaAprobada: null,
        onVentaRechazada: null,
        onError: null
    }
};

/**
 * Inicializa el módulo Getnet Linux
 * 
 * @param {Object} metaCaja - Metadatos de la caja { caja_codigo, cajero }
 * @param {Function} onVentaAprobada - Callback cuando venta es aprobada
 * @param {Function} onVentaRechazada - Callback cuando venta es rechazada
 * @param {Function} onError - Callback para errores
 */
export function initGetnetLinux(metaCaja, onVentaAprobada, onVentaRechazada, onError) {
    console.log('[Getnet Linux] Inicializando módulo...');
    
    estado.metaCaja = metaCaja;
    estado.callbacks.onVentaAprobada = onVentaAprobada;
    estado.callbacks.onVentaRechazada = onVentaRechazada;
    estado.callbacks.onError = onError;
    
    // Registrar callbacks según documentación Getnet
    Getnet.SetCallback(handleGetnetCallback);
    Getnet.SetLogCallback(handleGetnetLog);
    Getnet.SetTimeErrorCallback(handleGetnetTimeout);
    
    estado.inicializado = true;
    console.log('[Getnet Linux] Módulo inicializado correctamente');
}

/**
 * Conecta con el POS Getnet haciendo Poll
 * 
 * El navegador mostrará un diálogo para seleccionar el puerto COM/USB
 * la primera vez que se llama a Poll o cualquier comando.
 * 
 * @returns {Promise<boolean>} true si la conexión fue exitosa
 */
export async function conectarPos() {
    if (!estado.inicializado) {
        throw new Error('Getnet no está inicializado. Llama a initGetnetLinux primero.');
    }
    
    if (estado.puertoConectado) {
        console.log('[Getnet Linux] Puerto ya conectado');
        return true;
    }
    
    try {
        console.log('[Getnet Linux] Conectando POS (Poll)...');
        
        // Poll es el comando que establece comunicación con el POS
        // La primera vez, Chrome mostrará el diálogo de selección de puerto
        Getnet.Poll();
        
        // Nota: El callback manejará la confirmación de conexión
        // Por ahora asumimos que Poll inició el proceso
        estado.puertoConectado = true;
        
        return true;
    } catch (error) {
        console.error('[Getnet Linux] Error al conectar POS:', error);
        estado.puertoConectado = false;
        
        if (estado.callbacks.onError) {
            estado.callbacks.onError({
                tipo: 'conexion',
                mensaje: 'No se seleccionó el POS. Intenta nuevamente o pide ayuda al staff.',
                error: error
            });
        }
        
        return false;
    }
}

/**
 * Ejecuta una venta con tarjeta Getnet
 * 
 * @param {number} total - Monto total en pesos chilenos
 * @param {Array} carritoActual - Array de items del carrito
 * @returns {Promise<void>}
 */
export async function pagarGetnet(total, carritoActual) {
    if (!estado.inicializado) {
        throw new Error('Getnet no está inicializado');
    }
    
    // Validar monto
    if (!total || total <= 0) {
        throw new Error('Monto inválido');
    }
    
    // Asegurar que hay conexión con el POS
    if (!estado.puertoConectado) {
        console.log('[Getnet Linux] Conectando POS antes de venta...');
        const conectado = await conectarPos();
        if (!conectado) {
            throw new Error('No se pudo conectar con el POS');
        }
    }
    
    try {
        console.log(`[Getnet Linux] Ejecutando venta: $${total}`);
        
        // Guardar contexto de la venta para el callback
        estado.ventaActual = {
            total,
            carrito: carritoActual,
            timestamp: new Date()
        };
        
        // Ejecutar venta según documentación Getnet
        // Getnet.Sale(monto, ticketNumber, imprimirEnPOS, tipoVenta, usarCallback, employeeId)
        Getnet.Sale(
            total,                                    // monto
            estado.ticketNumber,                      // ticketNumber (TODO: secuencial)
            true,                                     // imprimir voucher en POS
            Getnet.POSCommands.SaleType.Sale,        // tipo de venta
            true,                                     // usar callback
            estado.employeeId                         // employeeId (TODO: real)
        );
        
        // Incrementar número de ticket para próxima venta
        estado.ticketNumber++;
        
        // El callback handleGetnetCallback procesará la respuesta
        
    } catch (error) {
        console.error('[Getnet Linux] Error al ejecutar venta:', error);
        
        if (estado.callbacks.onError) {
            estado.callbacks.onError({
                tipo: 'venta',
                mensaje: 'Error al procesar el pago. Intenta nuevamente.',
                error: error
            });
        }
        
        throw error;
    }
}

/**
 * Callback principal de Getnet
 * 
 * Procesa las respuestas del POS según la documentación:
 * - Si datos.Received es true, ignorar (mensaje de recepción)
 * - Parsear datos.JsonSerialized para obtener la respuesta real
 * - Verificar ResponseCode: "0" = aprobado, otro = rechazado
 * 
 * @param {Object} datos - Objeto con la respuesta del POS
 */
function handleGetnetCallback(datos) {
    console.log('[Getnet Linux] Callback recibido:', datos);
    
    // Según el ejemplo del simulador, ignorar si Received es true
    if (datos.Received === true) {
        console.log('[Getnet Linux] Mensaje de recepción, ignorando...');
        return;
    }
    
    try {
        // Parsear la respuesta JSON serializada
        const resp = JSON.parse(datos.JsonSerialized);
        console.log('[Getnet Linux] Respuesta parseada:', resp);
        
        // Verificar que sea una respuesta de venta
        // TODO: Verificar FunctionCode según documentación Getnet
        // Por ahora asumimos que cualquier respuesta con ResponseCode es válida
        
        if (resp.ResponseCode === "0") {
            // Venta aprobada
            console.log('[Getnet Linux] ✅ Venta aprobada');
            handleGetnetOK(resp, datos);
        } else {
            // Venta rechazada
            console.log('[Getnet Linux] ❌ Venta rechazada:', resp.ResponseCode);
            handleGetnetFail(resp, datos);
        }
        
    } catch (error) {
        console.error('[Getnet Linux] Error al parsear respuesta:', error);
        
        if (estado.callbacks.onError) {
            estado.callbacks.onError({
                tipo: 'parseo',
                mensaje: 'Error al procesar respuesta del POS',
                error: error
            });
        }
    }
}

/**
 * Maneja una venta aprobada por Getnet
 * 
 * Llama al backend /api/caja/venta-ok con los datos de la venta
 * y luego ejecuta el callback onVentaAprobada
 * 
 * @param {Object} resp - Respuesta parseada del POS
 * @param {Object} datos - Objeto original con JsonSerialized
 */
async function handleGetnetOK(resp, datos) {
    const ventaActual = estado.ventaActual;
    if (!ventaActual) {
        console.error('[Getnet Linux] No hay venta actual en estado');
        return;
    }
    
    try {
        // Preparar payload para backend
        const payload = {
            total: ventaActual.total,
            canal: "TOTEM",
            venta: {
                caja_codigo: estado.metaCaja.caja_codigo,
                cajero: estado.metaCaja.cajero,
                items: ventaActual.carrito
            },
            medio_pago: "TARJETA_GETNET",
            getnet: {
                responseCode: resp.ResponseCode,
                responseMessage: resp.ResponseMessage || "Aprobado",
                authorizationCode: resp.AuthorizationCode || null,
                ticketNumber: resp.Ticket || null,
                json: datos.JsonSerialized
            }
        };
        
        console.log('[Getnet Linux] Enviando venta OK al backend...');
        
        // Llamar al backend
        const response = await fetch('/api/caja/venta-ok', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }
        
        const resultado = await response.json();
        
        if (!resultado.ok) {
            throw new Error(resultado.error || 'Error al registrar venta');
        }
        
        console.log('[Getnet Linux] ✅ Venta registrada:', resultado);
        
        // Ejecutar callback de venta aprobada
        if (estado.callbacks.onVentaAprobada) {
            estado.callbacks.onVentaAprobada(resp, resultado);
        }
        
    } catch (error) {
        console.error('[Getnet Linux] Error al registrar venta OK:', error);
        
        if (estado.callbacks.onError) {
            estado.callbacks.onError({
                tipo: 'backend',
                mensaje: 'Error al registrar la venta. Contacta al administrador.',
                error: error
            });
        }
    }
}

/**
 * Maneja una venta rechazada por Getnet
 * 
 * Llama al backend /api/caja/venta-fallida-log y luego
 * ejecuta el callback onVentaRechazada
 * 
 * @param {Object} resp - Respuesta parseada del POS
 * @param {Object} datos - Objeto original con JsonSerialized
 */
async function handleGetnetFail(resp, datos) {
    const ventaActual = estado.ventaActual;
    if (!ventaActual) {
        console.error('[Getnet Linux] No hay venta actual en estado');
        return;
    }
    
    try {
        // Preparar payload para backend
        const payload = {
            total: ventaActual.total,
            venta: {
                caja_codigo: estado.metaCaja.caja_codigo,
                cajero: estado.metaCaja.cajero,
                items: ventaActual.carrito
            },
            motivo: resp.ResponseMessage || "No se pudo completar la operación",
            getnet: {
                responseCode: resp.ResponseCode,
                responseMessage: resp.ResponseMessage || "Rechazado",
                json: datos.JsonSerialized
            }
        };
        
        console.log('[Getnet Linux] Enviando venta fallida al backend...');
        
        // Llamar al backend (no crítico si falla)
        try {
            const response = await fetch('/api/caja/venta-fallida-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                const resultado = await response.json();
                console.log('[Getnet Linux] Log de venta fallida registrado');
            }
        } catch (backendError) {
            console.warn('[Getnet Linux] No se pudo registrar log de venta fallida:', backendError);
            // No es crítico, continuamos
        }
        
        // Ejecutar callback de venta rechazada
        if (estado.callbacks.onVentaRechazada) {
            estado.callbacks.onVentaRechazada(resp);
        }
        
    } catch (error) {
        console.error('[Getnet Linux] Error al manejar venta rechazada:', error);
        
        // Aún así, ejecutar callback para mostrar mensaje al usuario
        if (estado.callbacks.onVentaRechazada) {
            estado.callbacks.onVentaRechazada(resp);
        }
    }
}

/**
 * Callback de logs de Getnet
 * 
 * @param {string} mensaje - Mensaje de log del POS
 */
function handleGetnetLog(mensaje) {
    console.log('[Getnet POS Log]:', mensaje);
    // Opcional: enviar logs al backend para debugging
}

/**
 * Callback de timeout de Getnet
 * 
 * @param {Object} error - Error de timeout
 */
function handleGetnetTimeout(error) {
    console.error('[Getnet Linux] ⏱️ Timeout:', error);
    
    if (estado.callbacks.onError) {
        estado.callbacks.onError({
            tipo: 'timeout',
            mensaje: 'El POS no respondió a tiempo. Intenta nuevamente.',
            error: error
        });
    }
}

/**
 * Obtiene el estado actual del módulo
 */
export function getEstado() {
    return {
        inicializado: estado.inicializado,
        puertoConectado: estado.puertoConectado,
        ticketNumber: estado.ticketNumber
    };
}











