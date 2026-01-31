/**
 * Controlador del carrito y UI para tótem de autoatención
 * 
 * Este módulo controla:
 * - El carrito (agregar/eliminar ítems)
 * - El botón "Pagar con tarjeta"
 * - El botón "Cancelar compra"
 * - La integración con getnet_linux.js
 */

import { initGetnetLinux, conectarPos, pagarGetnet } from './getnet_linux.js';

/**
 * Estado del carrito y UI
 */
const estado = {
    carrito: [],
    total: 0,
    procesandoPago: false,
    metaCaja: {
        caja_codigo: "caja1",      // TODO: obtener de configuración o URL
        cajero: "TOTEM_AUTO_1"     // TODO: obtener de configuración o URL
    }
};

/**
 * Inicializa el módulo de caja tótem
 * 
 * Debe llamarse cuando se carga la página del tótem
 */
export function initCajaTotem() {
    console.log('[Caja Totem] Inicializando...');
    
    // Inicializar Getnet con callbacks
    initGetnetLinux(
        estado.metaCaja,
        onVentaAprobada,
        onVentaRechazada,
        onError
    );
    
    // Configurar event listeners
    setupEventListeners();
    
    // Cargar carrito desde localStorage si existe
    cargarCarritoDesdeStorage();
    
    // Actualizar UI inicial
    actualizarUI();
    
    console.log('[Caja Totem] Inicializado correctamente');
}

/**
 * Configura los event listeners de los botones
 */
function setupEventListeners() {
    // Botón "Pagar con tarjeta"
    const btnPagar = document.getElementById('btn-pagar-tarjeta');
    if (btnPagar) {
        btnPagar.addEventListener('click', handlePagarTarjeta);
    }
    
    // Botón "Cancelar compra"
    const btnCancelar = document.getElementById('btn-cancelar-compra');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', handleCancelarCompra);
    }
    
    // Botón "Volver a intentar" (se crea dinámicamente)
    document.addEventListener('click', (e) => {
        if (e.target.id === 'btn-reintentar-pago') {
            handleReintentarPago();
        }
    });
}

/**
 * Agrega un producto al carrito
 * 
 * @param {Object} producto - { sku, nombre, precio_unitario }
 * @param {number} cantidad - Cantidad a agregar (default: 1)
 */
export function agregarAlCarrito(producto, cantidad = 1) {
    const itemExistente = estado.carrito.find(item => item.sku === producto.sku);
    
    if (itemExistente) {
        itemExistente.cantidad += cantidad;
    } else {
        estado.carrito.push({
            sku: producto.sku,
            nombre: producto.nombre,
            cantidad: cantidad,
            precio_unitario: producto.precio_unitario
        });
    }
    
    calcularTotal();
    guardarCarritoEnStorage();
    actualizarUI();
}

/**
 * Elimina un producto del carrito
 * 
 * @param {string} sku - SKU del producto a eliminar
 */
export function eliminarDelCarrito(sku) {
    estado.carrito = estado.carrito.filter(item => item.sku !== sku);
    calcularTotal();
    guardarCarritoEnStorage();
    actualizarUI();
}

/**
 * Actualiza la cantidad de un producto en el carrito
 * 
 * @param {string} sku - SKU del producto
 * @param {number} cantidad - Nueva cantidad
 */
export function actualizarCantidad(sku, cantidad) {
    const item = estado.carrito.find(item => item.sku === sku);
    if (item) {
        if (cantidad <= 0) {
            eliminarDelCarrito(sku);
        } else {
            item.cantidad = cantidad;
            calcularTotal();
            guardarCarritoEnStorage();
            actualizarUI();
        }
    }
}

/**
 * Calcula el total del carrito
 */
function calcularTotal() {
    estado.total = estado.carrito.reduce((sum, item) => {
        return sum + (item.precio_unitario * item.cantidad);
    }, 0);
}

/**
 * Limpia el carrito completamente
 */
export function limpiarCarrito() {
    estado.carrito = [];
    estado.total = 0;
    guardarCarritoEnStorage();
    actualizarUI();
}

/**
 * Guarda el carrito en localStorage
 */
function guardarCarritoEnStorage() {
    try {
        localStorage.setItem('totem_carrito', JSON.stringify(estado.carrito));
    } catch (e) {
        console.warn('[Caja Totem] No se pudo guardar carrito en localStorage:', e);
    }
}

/**
 * Carga el carrito desde localStorage
 */
function cargarCarritoDesdeStorage() {
    try {
        const carritoGuardado = localStorage.getItem('totem_carrito');
        if (carritoGuardado) {
            estado.carrito = JSON.parse(carritoGuardado);
            calcularTotal();
        }
    } catch (e) {
        console.warn('[Caja Totem] No se pudo cargar carrito desde localStorage:', e);
    }
}

/**
 * Actualiza la UI del carrito
 */
function actualizarUI() {
    // Actualizar lista de productos
    const listaCarrito = document.getElementById('lista-carrito');
    if (listaCarrito) {
        listaCarrito.innerHTML = estado.carrito.map(item => `
            <div class="item-carrito" data-sku="${item.sku}">
                <span class="item-nombre">${item.nombre}</span>
                <span class="item-cantidad">x${item.cantidad}</span>
                <span class="item-precio">$${(item.precio_unitario * item.cantidad).toLocaleString('es-CL')}</span>
                <button class="btn-eliminar" onclick="eliminarDelCarrito('${item.sku}')">×</button>
            </div>
        `).join('');
    }
    
    // Actualizar total
    const totalElement = document.getElementById('total-carrito');
    if (totalElement) {
        totalElement.textContent = `$${estado.total.toLocaleString('es-CL')}`;
    }
    
    // Habilitar/deshabilitar botón de pago
    const btnPagar = document.getElementById('btn-pagar-tarjeta');
    if (btnPagar) {
        btnPagar.disabled = estado.carrito.length === 0 || estado.procesandoPago;
    }
    
    // Ocultar mensajes de error si existen
    ocultarMensajeError();
}

/**
 * Maneja el click en "Pagar con tarjeta"
 */
async function handlePagarTarjeta() {
    if (estado.carrito.length === 0) {
        mostrarError('El carrito está vacío');
        return;
    }
    
    if (estado.procesandoPago) {
        return; // Ya hay un pago en proceso
    }
    
    estado.procesandoPago = true;
    actualizarUI();
    
    try {
        // Asegurar conexión con POS
        const conectado = await conectarPos();
        if (!conectado) {
            mostrarError('No se pudo conectar con el POS. Intenta nuevamente.');
            estado.procesandoPago = false;
            actualizarUI();
            return;
        }
        
        // Ejecutar pago
        await pagarGetnet(estado.total, estado.carrito);
        
        // El callback onVentaAprobada o onVentaRechazada manejará el resultado
        
    } catch (error) {
        console.error('[Caja Totem] Error al procesar pago:', error);
        mostrarError('Error al procesar el pago. Intenta nuevamente.');
        estado.procesandoPago = false;
        actualizarUI();
    }
}

/**
 * Maneja el click en "Cancelar compra"
 */
function handleCancelarCompra() {
    if (confirm('¿Estás seguro de cancelar la compra?')) {
        limpiarCarrito();
        // Opcional: redirigir a pantalla inicial
        // window.location.href = '/totem';
    }
}

/**
 * Maneja el click en "Volver a intentar" después de un rechazo
 */
function handleReintentarPago() {
    ocultarMensajeError();
    estado.procesandoPago = false;
    actualizarUI();
    handlePagarTarjeta();
}

/**
 * Callback cuando una venta es aprobada
 * 
 * @param {Object} resp - Respuesta del POS Getnet
 * @param {Object} ventaBackend - Respuesta del backend con venta_id y ticket_code
 */
function onVentaAprobada(resp, ventaBackend) {
    console.log('[Caja Totem] ✅ Venta aprobada:', ventaBackend);
    
    estado.procesandoPago = false;
    
    // Abrir voucher en nueva ventana para impresión
    if (ventaBackend.venta_id) {
        const voucherUrl = `/voucher/${ventaBackend.venta_id}`;
        const ventanaVoucher = window.open(voucherUrl, '_blank');
        
        // La ventana imprimirá automáticamente (window.print() en voucher.html)
    }
    
    // Limpiar carrito
    limpiarCarrito();
    
    // Mostrar mensaje de éxito (opcional)
    mostrarExito('Pago procesado correctamente');
    
    // Opcional: redirigir a pantalla inicial después de un delay
    setTimeout(() => {
        // window.location.href = '/totem';
    }, 3000);
}

/**
 * Callback cuando una venta es rechazada
 * 
 * @param {Object} resp - Respuesta del POS Getnet
 */
function onVentaRechazada(resp) {
    console.log('[Caja Totem] ❌ Venta rechazada:', resp);
    
    estado.procesandoPago = false;
    actualizarUI();
    
    // Mostrar mensaje neutro (NO humillante)
    mostrarMensajeRechazo();
}

/**
 * Callback para errores
 * 
 * @param {Object} error - Objeto de error { tipo, mensaje, error }
 */
function onError(error) {
    console.error('[Caja Totem] Error:', error);
    
    estado.procesandoPago = false;
    actualizarUI();
    
    mostrarError(error.mensaje || 'Ocurrió un error. Intenta nuevamente.');
}

/**
 * Muestra mensaje de rechazo con botones de acción
 */
function mostrarMensajeRechazo() {
    const mensajeContainer = document.getElementById('mensaje-error');
    if (!mensajeContainer) {
        // Crear contenedor si no existe
        const container = document.createElement('div');
        container.id = 'mensaje-error';
        container.className = 'mensaje-rechazo';
        document.body.appendChild(container);
    }
    
    const mensajeContainer2 = document.getElementById('mensaje-error');
    mensajeContainer2.innerHTML = `
        <div class="mensaje-rechazo-contenido">
            <p class="mensaje-texto">No se pudo completar la operación. ¿Quieres volver a intentarlo?</p>
            <div class="botones-accion">
                <button id="btn-reintentar-pago" class="btn-reintentar">Volver a intentar</button>
                <button id="btn-cancelar-compra" class="btn-cancelar">Cancelar compra</button>
            </div>
        </div>
    `;
    
    mensajeContainer2.style.display = 'block';
}

/**
 * Muestra un mensaje de error genérico
 */
function mostrarError(mensaje) {
    const mensajeContainer = document.getElementById('mensaje-error');
    if (mensajeContainer) {
        mensajeContainer.innerHTML = `<p class="mensaje-error-texto">${mensaje}</p>`;
        mensajeContainer.style.display = 'block';
        
        // Ocultar después de 5 segundos
        setTimeout(() => {
            ocultarMensajeError();
        }, 5000);
    }
}

/**
 * Muestra un mensaje de éxito
 */
function mostrarExito(mensaje) {
    const mensajeContainer = document.getElementById('mensaje-exito');
    if (!mensajeContainer) {
        const container = document.createElement('div');
        container.id = 'mensaje-exito';
        container.className = 'mensaje-exito';
        document.body.appendChild(container);
    }
    
    const mensajeContainer2 = document.getElementById('mensaje-exito');
    mensajeContainer2.innerHTML = `<p class="mensaje-exito-texto">${mensaje}</p>`;
    mensajeContainer2.style.display = 'block';
    
    setTimeout(() => {
        mensajeContainer2.style.display = 'none';
    }, 3000);
}

/**
 * Oculta el mensaje de error
 */
function ocultarMensajeError() {
    const mensajeContainer = document.getElementById('mensaje-error');
    if (mensajeContainer) {
        mensajeContainer.style.display = 'none';
    }
}

/**
 * Obtiene el estado actual del carrito
 */
export function getEstadoCarrito() {
    return {
        carrito: [...estado.carrito],
        total: estado.total,
        procesandoPago: estado.procesandoPago
    };
}

// Inicializar cuando se carga el DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCajaTotem);
} else {
    initCajaTotem();
}











