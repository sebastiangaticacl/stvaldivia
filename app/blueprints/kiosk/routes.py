"""
Rutas del sistema de Kiosko
"""
from flask import render_template, request, jsonify, redirect, url_for, session, send_file, current_app
from datetime import datetime, timedelta
import logging
import os
from decimal import Decimal
import io
import base64
import barcode
from barcode.writer import ImageWriter
import qrcode

from ...models import db
from ...models.kiosk_models import Pago, PagoItem
from ...infrastructure.external.phppos_kiosk_client import PHPPosKioskClient
from ...infrastructure.external.sumup_client import SumUpClient
from . import kiosk_bp

logger = logging.getLogger(__name__)

# Decorador para eximir funciones de CSRF (para webhooks)
def exempt_from_csrf(func):
    """Decorador para marcar función como exenta de CSRF"""
    func._csrf_exempt = True
    return func

# Configuración del kiosko
TICKET_PREFIX = os.environ.get('KIOSK_TICKET_PREFIX', 'B')
KIOSKO_ID = os.environ.get('KIOSKO_ID', 'KIOSKO_1')
PHP_POS_REGISTER_ID = os.environ.get('PHP_POS_REGISTER_ID', '5')

# Inicializar clientes (se inicializan en cada request si es necesario)
def get_phppos_client():
    """Obtiene instancia del cliente PHP POS"""
    return PHPPosKioskClient()

def get_sumup_client():
    """Obtiene instancia del cliente SumUp"""
    return SumUpClient()

# Cache de productos (se actualiza periódicamente)
_productos_cache = None
_productos_cache_time = None
CACHE_DURATION = 300  # 5 minutos


def get_productos():
    """Obtiene lista de productos desde PHP POS API"""
    global _productos_cache, _productos_cache_time

    # MODO SOLO LOCAL: usar siempre productos de respaldo (sin API externa)
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            return _get_productos_fallback()
    except Exception:
        pass
    
    # Verificar si el cache es válido
    if _productos_cache and _productos_cache_time:
        if datetime.now() - _productos_cache_time < timedelta(seconds=CACHE_DURATION):
            logger.debug("Usando productos desde cache")
            return _productos_cache
    
    try:
        phppos_client = get_phppos_client()
        items = phppos_client.get_items(limit=1000)
        
        if not items:
            logger.warning("No se obtuvieron productos desde PHP POS. Usando lista de respaldo.")
            return _get_productos_fallback()
        
        # Transformar items de PHP POS al formato esperado por el frontend
        productos = []
        for item in items:
            item_id = str(item.get('item_id') or item.get('id') or '')
            nombre = item.get('name') or item.get('item_name') or 'Producto sin nombre'
            precio = float(item.get('unit_price') or item.get('price') or item.get('cost_price') or 0)
            
            # Obtener categoría y limpiar formato
            categoria_raw = item.get('category') or item.get('category_name') or 'Sin categoría'
            
            # Limpiar categoría: "Barra > Cervezas" -> "Cervezas"
            # También manejar casos como "Ninguno" o categorías sin ">"
            if ' > ' in categoria_raw:
                categoria = categoria_raw.split(' > ')[-1].strip()
            elif categoria_raw == 'Ninguno' or categoria_raw == 'Puerta':
                categoria = 'Otros'
            else:
                categoria = categoria_raw.strip()
            
            # Si no hay categoría válida, usar "Otros"
            if not categoria or categoria == 'Ninguno':
                categoria = 'Otros'
            
            if precio > 0 and item_id:
                productos.append({
                    'id': item_id,
                    'nombre': nombre,
                    'precio': precio,
                    'categoria': categoria
                })
        
        # Actualizar cache (global ya declarado al inicio de la función)
        _productos_cache = productos
        _productos_cache_time = datetime.now()
        
        logger.info(f"✅ Obtenidos {len(productos)} productos desde PHP POS")
        return productos
        
    except Exception as e:
        logger.error(f"Error al obtener productos desde PHP POS: {e}")
        return _get_productos_fallback()


def _get_productos_fallback():
    """Lista de productos de respaldo si falla la conexión con PHP POS"""
    return [
        {'id': '1', 'nombre': 'Piscola', 'precio': 5000, 'categoria': 'Piscolas'},
        {'id': '2', 'nombre': 'Piscola Doble', 'precio': 8000, 'categoria': 'Piscolas'},
        {'id': '3', 'nombre': 'Mojito', 'precio': 6000, 'categoria': 'Cocktails'},
        {'id': '4', 'nombre': 'Piña Colada', 'precio': 7000, 'categoria': 'Cocktails'},
        {'id': '5', 'nombre': 'Cerveza', 'precio': 3000, 'categoria': 'Cervezas'},
        {'id': '6', 'nombre': 'Cerveza Artesanal', 'precio': 5000, 'categoria': 'Cervezas'},
        {'id': '7', 'nombre': 'Agua', 'precio': 2000, 'categoria': 'Sin alcohol'},
        {'id': '8', 'nombre': 'Bebida', 'precio': 2500, 'categoria': 'Sin alcohol'},
    ]


def generate_ticket_code():
    """Genera un código de ticket único (B + sale_id) - Solo usado como respaldo"""
    last_pago = Pago.query.filter(Pago.ticket_code.isnot(None)).order_by(Pago.id.desc()).first()
    
    if last_pago and last_pago.ticket_code:
        try:
            last_num = int(last_pago.ticket_code.replace(TICKET_PREFIX, '').strip())
            next_num = last_num + 1
        except:
            next_num = 1
    else:
        next_num = 1
    
    return f"{TICKET_PREFIX} {next_num}"


# ============================================================================
# RUTAS DEL TÓTEM (Frontend)
# ============================================================================

@kiosk_bp.route('/')
def kiosk_home():
    """Pantalla de inicio del tótem"""
    # Verificar si el kiosko está habilitado
    if not current_app.config.get('KIOSK_ENABLED', False):
        return jsonify({'error': 'El kiosko está desactivado temporalmente'}), 503
    return render_template('kiosk/kiosk_home.html')


@kiosk_bp.route('/products')
def kiosk_products():
    """Pantalla de selección de productos"""
    # Verificar si el kiosko está habilitado
    if not current_app.config.get('KIOSK_ENABLED', False):
        return jsonify({'error': 'El kiosko está desactivado temporalmente'}), 503
    productos = get_productos()
    
    # Agrupar por categorías
    categorias = {}
    for producto in productos:
        cat = producto['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(producto)
    
    # Ordenar categorías de manera lógica
    # Orden preferido: Sin Alcohol primero, luego bebidas alcohólicas, luego otros
    orden_categorias = [
        'Sin Alcohol',
        'Cervezas',
        'Piscos',
        'Vodkas',
        'Rones',
        'Whiskies',
        'Tequilas',
        'Gines',
        'Vermut y Bitters',
        'Vinos y Espumantes',
        'Coctelería',
        'Mocktails',
        'Otros'
    ]
    
    # Crear diccionario ordenado
    categorias_ordenadas = {}
    # Primero agregar categorías en el orden preferido
    for cat in orden_categorias:
        if cat in categorias:
            categorias_ordenadas[cat] = categorias[cat]
    # Luego agregar cualquier categoría que no esté en la lista
    for cat, productos_cat in categorias.items():
        if cat not in categorias_ordenadas:
            categorias_ordenadas[cat] = productos_cat
    
    return render_template('kiosk/kiosk_products.html', categorias=categorias_ordenadas, productos=productos)


@kiosk_bp.route('/checkout', methods=['GET', 'POST'])
def kiosk_checkout():
    """Pantalla de confirmación de pedido"""
    # Verificar si el kiosko está habilitado
    if not current_app.config.get('KIOSK_ENABLED', False):
        return jsonify({'error': 'El kiosko está desactivado temporalmente'}), 503
    if request.method == 'POST':
        carrito_data = request.form.get('carrito')
        if not carrito_data:
            return redirect(url_for('kiosk.kiosk_products'))
        
        session['carrito'] = carrito_data
        return redirect(url_for('kiosk.kiosk_checkout'))
    
    carrito_data = session.get('carrito', '[]')
    
    # Verificar si SumUp está configurado
    sumup_enabled = bool(current_app.config.get('SUMUP_API_KEY'))
    
    return render_template('kiosk/kiosk_checkout.html', 
                         carrito_data=carrito_data,
                         sumup_enabled=sumup_enabled)


@kiosk_bp.route('/waiting')
def kiosk_waiting():
    """Pantalla de espera de pago"""
    pago_id = request.args.get('pago_id')
    if not pago_id:
        return redirect(url_for('kiosk.kiosk_home'))
    
    return render_template('kiosk/kiosk_waiting_payment.html', pago_id=pago_id)


@kiosk_bp.route('/sumup/payment/<int:pago_id>')
def kiosk_sumup_payment(pago_id):
    """Pantalla de pago con SumUp - muestra QR para escanear"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        if pago.estado != 'PENDING':
            # Si ya está pagado, redirigir a éxito
            if pago.estado == 'PAID':
                return redirect(url_for('kiosk.kiosk_success', pago_id=pago_id))
            # Si falló, volver al checkout
            return redirect(url_for('kiosk.kiosk_checkout'))
        
        # Generar QR code si no existe
        qr_image = None
        if pago.sumup_checkout_url:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(pago.sumup_checkout_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            qr_image = base64.b64encode(img_buffer.getvalue()).decode()
            qr_image = f"data:image/png;base64,{qr_image}"
        
        return render_template('kiosk/kiosk_sumup_payment.html', pago=pago, qr_image=qr_image)
    except Exception as e:
        logger.error(f"Error en kiosk_sumup_payment: {e}", exc_info=True)
        return redirect(url_for('kiosk.kiosk_home'))


@kiosk_bp.route('/success')
def kiosk_success():
    """Pantalla de pago aprobado con código/QR y código de barras"""
    pago_id = request.args.get('pago_id')
    if not pago_id:
        return redirect(url_for('kiosk.kiosk_home'))
    
    try:
        pago = Pago.query.get_or_404(int(pago_id))
        
        if pago.estado != 'PAID':
            return redirect(url_for('kiosk.kiosk_waiting', pago_id=pago_id))
        
        return render_template('kiosk/kiosk_success.html', pago=pago)
    except:
        return redirect(url_for('kiosk.kiosk_home'))


@kiosk_bp.route('/api/ticket/barcode/<ticket_code>')
def get_ticket_barcode(ticket_code):
    """Genera una imagen de código de barras para el ticket"""
    try:
        ticket_code_clean = ticket_code.replace(' ', '').replace(TICKET_PREFIX, '').strip()
        
        if ticket_code_clean.startswith(TICKET_PREFIX):
            barcode_text = ticket_code_clean.replace(TICKET_PREFIX, '').strip()
        else:
            barcode_text = ticket_code_clean
        
        logger.debug(f"Generando código de barras: '{barcode_text}' para ticket '{ticket_code}'")
        
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(barcode_text, writer=ImageWriter())
        
        img_buffer = io.BytesIO()
        barcode_instance.write(img_buffer)
        img_buffer.seek(0)
        
        return send_file(img_buffer, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error al generar código de barras: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error al generar código de barras: {str(e)}'}), 500


# ============================================================================
# API ENDPOINTS
# ============================================================================



@kiosk_bp.route('/api/pagos/status', methods=['GET'])
def api_pago_status():
    """Obtiene el estado de un pago"""
    try:
        pago_id = request.args.get('pago_id')
        if not pago_id:
            return jsonify({'ok': False, 'error': 'pago_id requerido'}), 400
        
        pago = Pago.query.get_or_404(int(pago_id))
        
        return jsonify({
            'ok': True,
            'estado': pago.estado,
            'ticket_code': pago.ticket_code
        })
        
    except Exception as e:
        logger.error(f"Error al obtener estado de pago: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500




@kiosk_bp.route('/api/productos', methods=['GET'])
def api_productos():
    """API para obtener lista de productos"""
    productos = get_productos()
    return jsonify({'ok': True, 'productos': productos})


@kiosk_bp.route('/api/pagos/sumup/create', methods=['POST'])
@exempt_from_csrf
def api_create_sumup_checkout():
    """Crea un checkout de SumUp para un pago del kiosko"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'ok': False, 'error': 'No se recibieron datos'}), 400
        
        carrito_items = data.get('carrito', [])
        if not carrito_items:
            return jsonify({'ok': False, 'error': 'Carrito vacío'}), 400
        
        # Calcular total
        total = sum(float(item.get('total', 0)) for item in carrito_items)
        if total <= 0:
            return jsonify({'ok': False, 'error': 'Monto inválido'}), 400
        
        # Crear registro de pago en estado PENDING
        pago = Pago(
            monto=Decimal(str(total)),
            moneda='CLP',
            estado='PENDING',
            metodo='SUMUP',
            kiosko_id=KIOSKO_ID
        )
        db.session.add(pago)
        db.session.flush()
        
        # Crear items del pago
        for item in carrito_items:
            pago_item = PagoItem(
                pago_id=pago.id,
                item_id_phppos=str(item.get('id', '')),
                nombre_item=item.get('nombre', 'Producto'),
                cantidad=int(item.get('cantidad', 1)),
                precio_unitario=Decimal(str(item.get('precio', 0))),
                total_linea=Decimal(str(item.get('total', 0)))
            )
            db.session.add(pago_item)
        
        # Generar referencia única para el checkout
        checkout_reference = f"KIOSK-{pago.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Construir return URL
        public_base_url = os.environ.get('PUBLIC_BASE_URL')
        if public_base_url:
            return_url = f"{public_base_url.rstrip('/')}{url_for('kiosk.sumup_payment_callback', pago_id=pago.id, _external=False)}"
        else:
            return_url = url_for('kiosk.sumup_payment_callback', pago_id=pago.id, _external=True)
        
        # Obtener merchant code de configuración
        merchant_code = current_app.config.get('SUMUP_MERCHANT_CODE')
        
        # Crear checkout en SumUp
        sumup_client = get_sumup_client()
        checkout_result = sumup_client.create_checkout(
            amount=total,
            currency='CLP',
            checkout_reference=checkout_reference,
            description=f"Kiosko {KIOSKO_ID} - Pedido #{pago.id}",
            return_url=return_url,
            merchant_code=merchant_code
        )
        
        if not checkout_result.get('success'):
            db.session.rollback()
            logger.error(f"Error al crear checkout SumUp: {checkout_result.get('error')}")
            return jsonify({
                'ok': False,
                'error': checkout_result.get('error', 'Error al crear checkout de pago')
            }), 500
        
        checkout_data = checkout_result.get('data', {})
        checkout_id = checkout_data.get('id')
        checkout_url = checkout_data.get('redirect_url') or checkout_data.get('href')
        
        # Actualizar pago con información de SumUp
        pago.sumup_checkout_id = checkout_id
        pago.sumup_checkout_url = checkout_url
        pago.sumup_merchant_code = merchant_code
        pago.transaction_id = checkout_id  # Mantener compatibilidad
        db.session.commit()
        
        logger.info(f"✅ Checkout SumUp creado: pago_id={pago.id}, checkout_id={checkout_id}")
        
        return jsonify({
            'ok': True,
            'pago_id': pago.id,
            'checkout_id': checkout_id,
            'checkout_url': checkout_url,
            'checkout_reference': checkout_reference
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear checkout SumUp: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@kiosk_bp.route('/api/pagos/sumup/qr/<int:pago_id>')
def api_get_sumup_qr(pago_id):
    """Genera un QR code con la URL del checkout SumUp"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        if not pago.sumup_checkout_url:
            return jsonify({'ok': False, 'error': 'No hay URL de checkout disponible'}), 404
        
        # Generar QR code con la URL del checkout
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(pago.sumup_checkout_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'ok': True,
            'qr_image': f"data:image/png;base64,{img_str}",
            'checkout_url': pago.sumup_checkout_url,
            'pago_id': pago.id
        })
        
    except Exception as e:
        logger.error(f"Error al generar QR SumUp: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@kiosk_bp.route('/sumup/callback/<int:pago_id>', methods=['GET', 'POST'])
@exempt_from_csrf
def sumup_payment_callback(pago_id):
    """Callback desde SumUp después del pago"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        logger.info(f"Callback SumUp recibido: pago_id={pago_id}, checkout_id={pago.sumup_checkout_id}")
        
        # Obtener checkout_id de parámetros o usar el guardado
        checkout_id = (
            request.args.get('checkout_id') or
            request.form.get('checkout_id') or
            request.args.get('id') or
            pago.sumup_checkout_id
        )
        
        if not checkout_id:
            logger.error(f"Callback sin checkout_id: pago_id={pago_id}")
            return redirect(url_for('kiosk.kiosk_checkout'))
        
        # Verificar estado del checkout en SumUp
        sumup_client = get_sumup_client()
        checkout_result = sumup_client.get_checkout(checkout_id)
        
        if not checkout_result.get('success'):
            logger.error(f"Error al obtener estado del checkout: {checkout_result.get('error')}")
            return redirect(url_for('kiosk.kiosk_waiting', pago_id=pago_id))
        
        checkout_data = checkout_result.get('data', {})
        checkout_status = checkout_data.get('status', '').upper()
        
        logger.info(f"Estado del checkout SumUp: {checkout_status} para pago_id={pago_id}")
        
        # Actualizar estado del pago
        if checkout_status == 'PAID':
            # Pago aprobado
            pago.estado = 'PAID'
            db.session.commit()
            
            # Sincronizar con PHP POS
            _sync_pago_to_phppos(pago)
            
            # Redirigir a pantalla de éxito
            return redirect(url_for('kiosk.kiosk_success', pago_id=pago_id))
        elif checkout_status in ('FAILED', 'EXPIRED'):
            # Pago rechazado o expirado
            pago.estado = 'FAILED'
            db.session.commit()
            return redirect(url_for('kiosk.kiosk_checkout'))
        else:
            # Estado pendiente
            return redirect(url_for('kiosk.kiosk_waiting', pago_id=pago_id))
        
    except Exception as e:
        logger.error(f"Error en callback SumUp: {e}", exc_info=True)
        return redirect(url_for('kiosk.kiosk_checkout'))


@kiosk_bp.route('/api/sumup/webhook', methods=['POST'])
@exempt_from_csrf
def sumup_webhook():
    """Webhook para recibir notificaciones de SumUp"""
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Webhook SumUp recibido sin datos")
            return jsonify({'ok': False, 'error': 'No data'}), 400
        
        logger.info(f"Webhook SumUp recibido: {data}")
        
        # Extraer información del webhook
        event_type = data.get('type', '')
        checkout_id = data.get('id') or data.get('checkout_id') or data.get('checkout', {}).get('id')
        
        if not checkout_id:
            logger.warning(f"Webhook SumUp sin checkout_id: {data}")
            return jsonify({'ok': False, 'error': 'No checkout_id'}), 400
        
        # Buscar pago por checkout_id
        pago = Pago.query.filter_by(sumup_checkout_id=checkout_id).first()
        
        if not pago:
            logger.warning(f"Pago no encontrado para checkout_id: {checkout_id}")
            return jsonify({'ok': False, 'error': 'Pago not found'}), 404
        
        # Procesar según tipo de evento
        if event_type in ('checkout.succeeded', 'checkout.paid'):
            # Pago exitoso
            pago.estado = 'PAID'
            db.session.commit()
            
            # Sincronizar con PHP POS
            _sync_pago_to_phppos(pago)
            
            logger.info(f"✅ Pago marcado como PAID vía webhook: pago_id={pago.id}, checkout_id={checkout_id}")
        elif event_type in ('checkout.failed', 'checkout.expired'):
            # Pago fallido o expirado
            pago.estado = 'FAILED'
            db.session.commit()
            logger.info(f"⚠️ Pago marcado como FAILED vía webhook: pago_id={pago.id}, checkout_id={checkout_id}")
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Error en webhook SumUp: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


def _sync_pago_to_phppos(pago: Pago):
    """Sincroniza un pago confirmado con PHP POS"""
    try:
        if pago.sale_id_phppos:
            logger.info(f"Pago {pago.id} ya sincronizado con PHP POS (sale_id={pago.sale_id_phppos})")
            return
        
        # Preparar items para PHP POS
        items = []
        for item in pago.items:
            items.append({
                'item_id': item.item_id_phppos,
                'quantity': item.cantidad,
                'price': float(item.precio_unitario)
            })
        
        # Crear venta en PHP POS
        phppos_client = get_phppos_client()
        sale_result = phppos_client.create_sale(
            items=items,
            total=float(pago.monto),
            payment_type='SumUp',
            register_id=PHP_POS_REGISTER_ID
        )
        
        if sale_result.get('success'):
            sale_id = sale_result.get('sale_id')
            pago.sale_id_phppos = str(sale_id)
            
            # Generar ticket code
            if not pago.ticket_code:
                receipt_code = sale_result.get('receipt_code')
                if receipt_code:
                    pago.ticket_code = receipt_code
                else:
                    pago.ticket_code = generate_ticket_code()
            
            db.session.commit()
            logger.info(f"✅ Pago {pago.id} sincronizado con PHP POS: sale_id={sale_id}")
        else:
            logger.error(f"Error al sincronizar pago {pago.id} con PHP POS: {sale_result.get('error')}")
        
    except Exception as e:
        logger.error(f"Error al sincronizar pago {pago.id} con PHP POS: {e}", exc_info=True)
        # No hacer rollback aquí, el pago ya está marcado como PAID

