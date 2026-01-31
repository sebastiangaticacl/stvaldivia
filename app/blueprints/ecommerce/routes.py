"""
Rutas para el sistema de Ecommerce - Venta de Entradas Express con GetNet
"""
import logging
import json
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, redirect, url_for, session, flash, current_app
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from flask import Response
from decimal import Decimal
from . import ecommerce_bp
from app.models import db
from app.models.ecommerce_models import Entrada, CheckoutSession
from app.helpers.getnet_web_helper import (
    create_getnet_payment,
    get_getnet_payment_status,
    is_payment_approved,
    extract_payment_info
)
# Intentar también con helper PlaceToPay (GetNet usa PlaceToPay como base)
try:
    from app.helpers.getnet_placepay_helper import create_getnet_payment_placetopay
except ImportError:
    create_getnet_payment_placetopay = None
from app.helpers.rut_validator import validate_rut, format_rut, clean_rut
from app.helpers.email_ticket_helper import send_ticket_email

logger = logging.getLogger(__name__)

# Decorador para eximir funciones de CSRF
# Este decorador marca la función para que sea eximida cuando se registre
def exempt_from_csrf(func):
    """Decorador para marcar función como exenta de CSRF"""
    # Marcar la función para que sea eximida después del registro
    func._csrf_exempt = True
    return func

# Importar rutas de debug (solo en desarrollo)
try:
    from . import debug_routes
except ImportError:
    pass


@ecommerce_bp.route('/landing', methods=['GET', 'POST'])
@exempt_from_csrf
def landing():
    """Landing page moderna para el producto principal del ecommerce con formulario de compra"""
    if request.method == 'POST':
        # Procesar formulario de compra (misma lógica que checkout POST)
        try:
            from app.models.product_models import Product
            
            data = request.form
            
            # Validar datos requeridos
            comprador_nombre = data.get('nombre', '').strip()
            comprador_email = data.get('email', '').strip()
            comprador_rut = data.get('rut', '').strip()
            comprador_telefono = data.get('telefono', '').strip()
            product_id = data.get('producto_id', type=int)
            cantidad = int(data.get('cantidad', 1))
            precio_unitario = Decimal(data.get('precio_unitario', 0))
            precio_total = Decimal(data.get('precio_total', 0))
            
            # Validar producto
            if not product_id:
                flash('Producto no especificado', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            producto = Product.query.get(product_id)
            
            if not producto:
                logger.warning(f"[POST Landing] Producto no encontrado: product_id={product_id}")
                flash('Producto no encontrado', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            # Verificar categoría case-insensitive (acepta ENTRADAS, Entradas, entrada, etc.)
            categoria_ok = producto.category and producto.category.upper() in ['ENTRADAS', 'ENTRADA']
            if not categoria_ok:
                logger.warning(f"[POST Landing] Producto categoría incorrecta: product_id={product_id}, categoria='{producto.category}'")
                flash('Producto no disponible: categoría incorrecta', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            if not producto.is_active:
                logger.warning(f"[POST Landing] Producto inactivo: product_id={product_id}")
                flash('Producto no disponible: producto inactivo', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            # Validar stock disponible
            stock_disponible = producto.stock_quantity
            if stock_disponible is not None:
                if stock_disponible <= 0:
                    flash('Este producto está agotado', 'error')
                    return redirect(url_for('ecommerce.landing'))
                if cantidad > stock_disponible:
                    flash(f'Solo hay {stock_disponible} unidad(es) disponible(s)', 'error')
                    return redirect(url_for('ecommerce.landing'))
            
            # Valores por defecto si están vacíos
            if not comprador_nombre:
                comprador_nombre = 'Cliente'
            if not comprador_email:
                comprador_email = 'cliente@ejemplo.com'
            
            # Validar límite de 2 entradas por persona
            if cantidad > 2:
                flash('Solo se pueden comprar máximo 2 entradas por persona', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            if cantidad <= 0 or precio_total <= 0:
                flash('Cantidad y precio deben ser mayores a 0', 'error')
                return redirect(url_for('ecommerce.landing'))
            
            # Crear sesión de checkout
            checkout_session = CheckoutSession(
                session_id=CheckoutSession.generate_session_id(),
                evento_nombre=producto.name,
                evento_fecha=datetime.utcnow(),
                evento_lugar='BIMBA',
                comprador_nombre=comprador_nombre,
                comprador_email=comprador_email,
                comprador_rut=comprador_rut,
                comprador_telefono=comprador_telefono,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                precio_total=precio_total,
                estado='iniciado',
                expires_at=datetime.utcnow() + timedelta(minutes=30)
            )
            
            db.session.add(checkout_session)
            db.session.flush()
            
            # Procesar pago directamente (sin GetNet)
            # Simular pago aprobado para crear la entrada inmediatamente
            from app.models.ecommerce_models import Entrada
            
            # Validar stock antes de procesar (doble verificación)
            if producto.stock_quantity is not None:
                if producto.stock_quantity < cantidad:
                    db.session.rollback()
                    flash(f'Solo hay {producto.stock_quantity} unidad(es) disponible(s)', 'error')
                    return redirect(url_for('ecommerce.landing'))
            
            # Asegurar que precio_total sea correcto (cantidad * precio_unitario)
            precio_total_calculado = cantidad * precio_unitario
            
            # Crear entrada directamente con estado "recibido"
            entrada = Entrada(
                ticket_code=Entrada.generate_ticket_code(),
                evento_nombre=producto.name,
                evento_fecha=datetime.utcnow(),
                evento_lugar='BIMBA',
                comprador_nombre=comprador_nombre,
                comprador_email=comprador_email,
                comprador_rut=comprador_rut,
                comprador_telefono=comprador_telefono,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                precio_total=precio_total_calculado,
                estado_pago='recibido',  # Estado inicial: recibido
                metodo_pago='manual',
                # paid_at se actualizará cuando se confirme el pago
            )
            
            db.session.add(entrada)
            db.session.flush()
            
            # Actualizar stock del inventario si el producto tiene stock limitado
            if producto.stock_quantity is not None:
                producto.stock_quantity -= cantidad
                if producto.stock_quantity < 0:
                    producto.stock_quantity = 0  # No permitir stock negativo
                producto.updated_at = datetime.utcnow()
                logger.info(f"Stock actualizado para {producto.name}: {producto.stock_quantity + cantidad} -> {producto.stock_quantity}")
            
            # Actualizar checkout session
            checkout_session.estado = 'completado'
            checkout_session.completed_at = datetime.utcnow()
            checkout_session.entrada_id = entrada.id
            db.session.commit()
            
            # Enviar email de bienvenida al comprador (con QR y link de pago)
            try:
                from app.helpers.email_ticket_helper import send_resumen_compra_email
                send_resumen_compra_email(entrada)
                logger.info(f"Email de bienvenida enviado a {comprador_email}")
            except Exception as email_error:
                logger.warning(f"No se pudo enviar email de bienvenida: {email_error}")
            
            # También enviar notificación al admin
            try:
                send_ticket_email(entrada)
            except Exception as email_error:
                logger.warning(f"No se pudo enviar email de notificación al admin: {email_error}")
            
            # Redirigir a confirmación
            return redirect(url_for('ecommerce.confirmation', ticket_code=entrada.ticket_code))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en landing POST: {e}", exc_info=True)
            flash('Error al procesar el checkout. Por favor intenta nuevamente.', 'error')
            return redirect(url_for('ecommerce.landing'))
    
    # GET: Mostrar landing page
    try:
        from app.models.product_models import Product
        from sqlalchemy import func
        
        # Obtener el primer producto activo de categoría ENTRADAS/Entradas con stock disponible
        # Buscar con comparación case-insensitive (acepta "Entradas", "ENTRADAS", "entradas", etc.)
        producto = Product.query.filter(
            func.upper(Product.category) == 'ENTRADAS',
            Product.is_active == True
        ).filter(
            # Stock disponible: mayor a 0 o NULL (ilimitado)
            db.or_(
                Product.stock_quantity > 0,
                Product.stock_quantity.is_(None)
            )
        ).order_by(Product.price.asc(), Product.name.asc()).first()
        
        if producto:
            stock_qty = producto.stock_quantity if producto.stock_quantity is not None else None
            precio_unitario = float(producto.price) if producto.price else 0.0
            producto_data = {
                'id': producto.id,
                'nombre': producto.name,
                'precio': producto.price,
                'precio_unitario': precio_unitario,
                'categoria': producto.category,
                'stock_quantity': stock_qty,
                'disponible': stock_qty is None or stock_qty > 0,
                'stock_ilimitado': stock_qty is None
            }
            logger.info(f"Producto encontrado para landing: {producto_data['nombre']}, precio: {producto_data['precio']}")
        else:
            producto_data = None
            logger.warning("No se encontró producto para landing page")
        
        return render_template('ecommerce/landing.html', producto=producto_data)
        
    except Exception as e:
        logger.error(f"Error al cargar producto para landing: {e}", exc_info=True)
        return render_template('ecommerce/landing.html', producto=None)


@ecommerce_bp.route('/')
def index():
    """Página principal de venta de entradas - Muestra productos de categoría ENTRADAS con stock disponible"""
    try:
        from app.models.product_models import Product
        from sqlalchemy import func
        
        # Obtener productos activos de categoría ENTRADAS/Entradas con stock disponible
        # Para ENTRADAS, consideramos disponible si:
        # - is_active = True
        # - stock_quantity > 0 (o stock_quantity es NULL, lo que significa stock ilimitado)
        # Usamos comparación case-insensitive para la categoría (acepta "Entradas", "ENTRADAS", etc.)
        productos = Product.query.filter(
            func.upper(Product.category) == 'ENTRADAS',
            Product.is_active == True
        ).filter(
            # Stock disponible: mayor a 0 o NULL (ilimitado)
            db.or_(
                Product.stock_quantity > 0,
                Product.stock_quantity.is_(None)
            )
        ).order_by(Product.price.asc(), Product.name.asc()).all()
        
        # Preparar datos de productos para el template
        productos_data = []
        for producto in productos:
            stock_qty = producto.stock_quantity if producto.stock_quantity is not None else None
            disponible = stock_qty is None or stock_qty > 0
            
            productos_data.append({
                'id': producto.id,
                'nombre': producto.name,
                'precio': producto.price,
                'categoria': producto.category,
                'stock_quantity': stock_qty,
                'disponible': disponible,
                'stock_ilimitado': stock_qty is None
            })
        
        return render_template('ecommerce/index.html', productos=productos_data)
        
    except Exception as e:
        logger.error(f"Error al cargar productos: {e}", exc_info=True)
        # Si hay error, mostrar página sin productos
        return render_template('ecommerce/index.html', productos=[])


@ecommerce_bp.route('/checkout', methods=['GET', 'POST'])
@exempt_from_csrf
def checkout():
    """
    Checkout express para venta de entradas (productos)
    
    GET: Muestra formulario de checkout
    POST: Procesa datos y crea sesión de checkout
    """
    if request.method == 'GET':
        from app.models.product_models import Product
        
        # Obtener parámetros de la URL (product_id, cantidad)
        product_id = request.args.get('product_id', type=int)
        cantidad = int(request.args.get('cantidad', 1))
        
        # Validar producto
        if not product_id:
            flash('Producto no especificado', 'error')
            return redirect(url_for('ecommerce.index'))
        
        producto = Product.query.get(product_id)
        
        # Debug logging
        if not producto:
            logger.warning(f"[GET] Producto no encontrado: product_id={product_id}")
            flash('Producto no encontrado', 'error')
            return redirect(url_for('ecommerce.index'))
        
        # Verificar categoría case-insensitive
        categoria_ok = producto.category and producto.category.upper() == 'ENTRADAS'
        if not categoria_ok:
            logger.warning(f"[GET] Producto categoría incorrecta: product_id={product_id}, categoria='{producto.category}', is_active={producto.is_active}")
            flash('Producto no disponible: categoría incorrecta', 'error')
            return redirect(url_for('ecommerce.index'))
        
        if not producto.is_active:
            logger.warning(f"[GET] Producto inactivo: product_id={product_id}, categoria='{producto.category}', is_active={producto.is_active}")
            flash('Producto no disponible: producto inactivo', 'error')
            return redirect(url_for('ecommerce.index'))
        
        logger.info(f"[GET] Producto validado correctamente: product_id={product_id}, nombre='{producto.name}', categoria='{producto.category}'")
        
        precio_unitario = float(producto.price) if producto.price else 0.0
        precio_total = cantidad * precio_unitario
        
        return render_template('ecommerce/checkout.html',
                             producto_id=producto.id,
                             producto_nombre=producto.name,
                             cantidad=cantidad,
                             precio_unitario=precio_unitario,
                             precio_total=precio_total)
    
    # POST: Procesar datos del formulario
    try:
        from app.models.product_models import Product
        
        data = request.form
        
        # Validar datos requeridos
        comprador_nombre = data.get('nombre', '').strip()
        comprador_email = data.get('email', '').strip()
        comprador_rut = data.get('rut', '').strip()
        comprador_telefono = data.get('telefono', '').strip()
        product_id = data.get('producto_id', type=int)
        cantidad = int(data.get('cantidad', 1))
        precio_unitario = Decimal(data.get('precio_unitario', 0))
        precio_total = Decimal(data.get('precio_total', 0))
        
        # Validar producto
        if not product_id:
            flash('Producto no especificado', 'error')
            return redirect(url_for('ecommerce.index'))
        
        producto = Product.query.get(product_id)
        
        # Debug logging
        if not producto:
            logger.warning(f"[POST] Producto no encontrado: product_id={product_id}")
            flash('Producto no encontrado', 'error')
            return redirect(url_for('ecommerce.index'))
        
        # Verificar categoría case-insensitive
        categoria_ok = producto.category and producto.category.upper() == 'ENTRADAS'
        if not categoria_ok:
            logger.warning(f"[POST] Producto categoría incorrecta: product_id={product_id}, categoria='{producto.category}', is_active={producto.is_active}")
            flash('Producto no disponible: categoría incorrecta', 'error')
            return redirect(url_for('ecommerce.index'))
        
        if not producto.is_active:
            logger.warning(f"[POST] Producto inactivo: product_id={product_id}, categoria='{producto.category}', is_active={producto.is_active}")
            flash('Producto no disponible: producto inactivo', 'error')
            return redirect(url_for('ecommerce.index'))
        
        logger.info(f"[POST] Producto validado correctamente: product_id={product_id}, nombre='{producto.name}', categoria='{producto.category}'")
        
        # Validar stock disponible
        stock_disponible = producto.stock_quantity
        if stock_disponible is not None:  # Si tiene stock limitado
            if stock_disponible <= 0:
                flash('Este producto está agotado', 'error')
                return redirect(url_for('ecommerce.index'))
            if cantidad > stock_disponible:
                flash(f'Solo hay {stock_disponible} unidad(es) disponible(s)', 'error')
                return redirect(url_for('ecommerce.checkout', product_id=product_id, cantidad=min(cantidad, stock_disponible)))
        
        # Valores por defecto si están vacíos
        if not comprador_nombre:
            comprador_nombre = 'Cliente'
        if not comprador_email:
            comprador_email = 'cliente@ejemplo.com'
        
        if cantidad <= 0 or precio_total <= 0:
            flash('Cantidad y precio deben ser mayores a 0', 'error')
            return redirect(url_for('ecommerce.checkout', product_id=product_id, cantidad=cantidad))
        
        # Usar evento_nombre para almacenar el nombre del producto
        # evento_fecha será la fecha actual (para compatibilidad con el modelo)
        # evento_lugar será "BIMBA" por defecto
        
        # Crear sesión de checkout
        checkout_session = CheckoutSession(
            session_id=CheckoutSession.generate_session_id(),
            evento_nombre=producto.name,  # Usar nombre del producto
            evento_fecha=datetime.utcnow(),  # Fecha actual
            evento_lugar='BIMBA',  # Lugar por defecto
            comprador_nombre=comprador_nombre,
            comprador_email=comprador_email,
            comprador_rut=comprador_rut,
            comprador_telefono=comprador_telefono,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            precio_total=precio_total,
            estado='iniciado',
            expires_at=datetime.utcnow() + timedelta(minutes=30)  # Expira en 30 minutos
        )
        
        db.session.add(checkout_session)
        db.session.commit()
        
        # Guardar session_id en la sesión del usuario
        session['checkout_session_id'] = checkout_session.session_id
        
        # Redirigir a procesamiento de pago
        return redirect(url_for('ecommerce.process_payment', session_id=checkout_session.session_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en checkout: {e}", exc_info=True)
        flash('Error al procesar el checkout. Por favor intenta nuevamente.', 'error')
        return redirect(url_for('ecommerce.index'))


@ecommerce_bp.route('/payment/<session_id>', methods=['GET', 'POST'])
def process_payment(session_id):
    """
    Procesa el pago usando GetNet Web Checkout
    
    GET: Redirige a GetNet Web Checkout
    POST: Callback desde GetNet (no usado aquí, se maneja en payment_callback)
    """
    checkout_session = CheckoutSession.query.filter_by(session_id=session_id).first()
    
    if not checkout_session:
        flash('Sesión de checkout no encontrada', 'error')
        return redirect(url_for('ecommerce.index'))
    
    if checkout_session.is_expired():
        checkout_session.estado = 'expirado'
        db.session.commit()
        flash('La sesión de checkout expiró. Por favor inicia nuevamente.', 'error')
        return redirect(url_for('ecommerce.index'))
    
    if checkout_session.estado == 'completado':
        # Ya está completado, redirigir a confirmación
        if checkout_session.entrada_id:
            entrada = Entrada.query.get(checkout_session.entrada_id)
            if entrada:
                return redirect(url_for('ecommerce.confirmation', ticket_code=entrada.ticket_code))
        flash('Error: Sesión completada pero entrada no encontrada', 'error')
        return redirect(url_for('ecommerce.index'))
    
    # Si ya tiene payment_intent_id, verificar estado
    if checkout_session.payment_intent_id:
        payment_status = get_getnet_payment_status(checkout_session.payment_intent_id)
        if payment_status and is_payment_approved(payment_status):
            # Pago ya aprobado, procesar
            return _process_approved_payment(checkout_session, payment_status)
    
    # Crear nuevo payment en GetNet
    try:
        # Preparar datos del cliente
        nombre_parts = checkout_session.comprador_nombre.split(maxsplit=1)
        customer_data = {
            'first_name': nombre_parts[0] if nombre_parts else '',
            'last_name': nombre_parts[1] if len(nombre_parts) > 1 else '',
            'email': checkout_session.comprador_email,
            'phone_number': checkout_session.comprador_telefono or '',
            'document_number': clean_rut(checkout_session.comprador_rut) if checkout_session.comprador_rut else '',
            'city': 'Santiago',
        }
        
        # URLs de callback (GetNet necesita URLs públicas accesibles desde internet)
        public_base_url = current_app.config.get('PUBLIC_BASE_URL')
        
        # En desarrollo local, usar la URL del request si no hay PUBLIC_BASE_URL configurado
        if not public_base_url:
            # Intentar obtener desde el request actual
            if request and hasattr(request, 'url_root'):
                # Extraer el base URL del request (ej: http://127.0.0.1:5001)
                from urllib.parse import urlparse
                parsed = urlparse(request.url_root)
                public_base_url = f"{parsed.scheme}://{parsed.netloc}"
                logger.info(f"Usando URL del request como PUBLIC_BASE_URL: {public_base_url}")
            else:
                # Fallback a _external=True
                try:
                    return_url_temp = url_for('ecommerce.payment_callback', session_id=session_id, _external=True)
                    from urllib.parse import urlparse
                    parsed = urlparse(return_url_temp)
                    public_base_url = f"{parsed.scheme}://{parsed.netloc}"
                except:
                    public_base_url = None
        
        if public_base_url:
            # Usar URL pública configurada
            return_url = f"{public_base_url.rstrip('/')}{url_for('ecommerce.payment_callback', session_id=session_id)}"
            cancel_url = f"{public_base_url.rstrip('/')}{url_for('ecommerce.payment_cancelled', session_id=session_id)}"
        else:
            # Fallback a _external=True (puede no funcionar en desarrollo local)
            return_url = url_for('ecommerce.payment_callback', session_id=session_id, _external=True)
            cancel_url = url_for('ecommerce.payment_cancelled', session_id=session_id, _external=True)
        
        logger.info(f"Return URL: {return_url}")
        logger.info(f"Cancel URL: {cancel_url}")
        logger.info(f"Public Base URL usado: {public_base_url}")
        
        # Metadata adicional
        metadata = {
            'evento_nombre': checkout_session.evento_nombre,
            'evento_fecha': checkout_session.evento_fecha.isoformat() if checkout_session.evento_fecha else '',
        }
        
        # Crear pago en GetNet
        logger.info(f"Intentando crear pago en GetNet para sesión: {session_id}")
        logger.info(f"Monto: {checkout_session.precio_total}, Currency: CLP")
        
        # Intentar primero con método PlaceToPay (estándar de GetNet)
        payment_result = None
        if create_getnet_payment_placetopay:
            try:
                logger.info("Intentando crear pago con método PlaceToPay/GetNet estándar")
                payment_result = create_getnet_payment_placetopay(
                    amount=float(checkout_session.precio_total),
                    currency='CLP',
                    order_id=checkout_session.session_id,
                    customer_data=customer_data,
                    return_url=return_url,
                    cancel_url=cancel_url,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Error con método PlaceToPay, intentando método alternativo: {e}")
        
        # Si PlaceToPay falla, intentar método alternativo
        if not payment_result:
            try:
                logger.info("Intentando crear pago con método alternativo")
                payment_result = create_getnet_payment(
                    amount=float(checkout_session.precio_total),
                    currency='CLP',
                    order_id=checkout_session.session_id,
                    customer_data=customer_data,
                    return_url=return_url,
                    cancel_url=cancel_url,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"Excepción al crear pago en GetNet: {e}", exc_info=True)
                flash('Error al conectar con el sistema de pagos. Por favor intenta más tarde.', 'error')
                return redirect(url_for('ecommerce.index'))
        
        if not payment_result:
            # Obtener información de configuración para debug
            from app.helpers.getnet_web_helper import get_getnet_config, get_getnet_auth_headers
            config = get_getnet_config()
            headers = get_getnet_auth_headers()
            
            error_details = {
                'session_id': checkout_session.session_id,
                'amount': float(checkout_session.precio_total),
                'api_base_url': config.get('api_base_url'),
                'login_configured': bool(config.get('login')),
                'trankey_configured': bool(config.get('trankey')),
                'headers_obtained': bool(headers),
            }
            
            logger.error("No se pudo crear pago en GetNet - payment_result es None")
            logger.error(f"Checkout session: {checkout_session.session_id}, amount: {checkout_session.precio_total}")
            logger.error(f"Return URL: {return_url}")
            logger.error(f"Cancel URL: {cancel_url}")
            logger.error(f"Config GetNet: api_base_url={config.get('api_base_url')}, login={bool(config.get('login'))}, trankey={bool(config.get('trankey'))}")
            logger.error(f"Headers obtenidos: {bool(headers)}")
            
            # Mensaje de error más descriptivo según el contexto
            public_url = current_app.config.get('PUBLIC_BASE_URL')
            is_demo = config.get('demo_mode', False)
            
            error_msg = 'Error al conectar con el sistema de pagos. '
            if not config.get('login') or not config.get('trankey'):
                error_msg += 'Credenciales de GetNet no configuradas. Contacta al administrador.'
            elif not public_url and not is_demo:
                error_msg += 'Se requiere PUBLIC_BASE_URL configurado para pagos online. Contacta al administrador.'
            elif not headers:
                error_msg += 'No se pudieron obtener headers de autenticación. Verifica las credenciales.'
            else:
                error_msg += 'Por favor intenta más tarde.'
            
            if current_app.config.get('DEBUG', False):
                error_msg += f' (Debug: {error_details})'
            
            flash(error_msg, 'error')
            
            # Redirigir de vuelta al index (no podemos reconstruir product_id desde checkout_session)
            return redirect(url_for('ecommerce.index'))
        
        # Guardar payment_intent_id
        checkout_session.payment_intent_id = payment_result.get('payment_id')
        db.session.commit()
        
        # Redirigir a GetNet Web Checkout
        checkout_url = payment_result.get('checkout_url')
        
        if checkout_url:
            logger.info(f"Redirigiendo a GetNet Web Checkout: session_id={session_id}, payment_id={checkout_session.payment_intent_id}")
            return redirect(checkout_url)
        else:
            flash('Error: No se recibió URL de checkout de GetNet', 'error')
            logger.error(f"GetNet no retornó checkout_url: {payment_result}")
            return redirect(url_for('ecommerce.checkout'))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al procesar pago con GetNet: {e}", exc_info=True)
        flash('Error al procesar el pago. Por favor intenta más tarde.', 'error')
        return redirect(url_for('ecommerce.checkout'))


def _process_approved_payment(checkout_session: CheckoutSession, payment_status: dict):
    """
    Procesa un pago aprobado: crea la entrada y redirige a confirmación
    
    Args:
        checkout_session: Sesión de checkout
        payment_status: Estado del pago de GetNet
        
    Returns:
        Redirect a confirmación
    """
    try:
        from app.models.product_models import Product
        
        payment_info = extract_payment_info(payment_status)
        
        # Buscar el producto por nombre (evento_nombre contiene el nombre del producto)
        # Usar comparación case-insensitive para la categoría
        producto = Product.query.filter(
            Product.name == checkout_session.evento_nombre,
            func.upper(Product.category) == 'ENTRADAS',
            Product.is_active == True
        ).first()
        
        # Validar stock antes de procesar (doble verificación)
        if producto and producto.stock_quantity is not None:
            if producto.stock_quantity < checkout_session.cantidad:
                logger.error(f"Stock insuficiente para producto {producto.name}. Stock: {producto.stock_quantity}, Solicitado: {checkout_session.cantidad}")
                flash('Stock insuficiente. El producto ya no está disponible.', 'error')
                return redirect(url_for('ecommerce.index'))
        
        # Asegurar que precio_total sea correcto (cantidad * precio_unitario)
        precio_total_calculado = float(checkout_session.cantidad) * float(checkout_session.precio_unitario)
        
        # Crear entrada con estado "recibido" inicialmente
        entrada = Entrada(
            ticket_code=Entrada.generate_ticket_code(),
            evento_nombre=checkout_session.evento_nombre,
            evento_fecha=checkout_session.evento_fecha,
            evento_lugar=checkout_session.evento_lugar,
            comprador_nombre=checkout_session.comprador_nombre,
            comprador_email=checkout_session.comprador_email,
            comprador_rut=checkout_session.comprador_rut,
            comprador_telefono=checkout_session.comprador_telefono,
            cantidad=checkout_session.cantidad,
            precio_unitario=checkout_session.precio_unitario,
            precio_total=precio_total_calculado,
            estado_pago='recibido',  # Estado inicial: recibido
            metodo_pago='getnet_web',
            getnet_payment_id=payment_info.get('payment_id'),
            getnet_transaction_id=payment_info.get('transaction_id'),
            getnet_auth_code=payment_info.get('auth_code'),
            # paid_at se actualizará cuando se confirme el pago
        )
        
        db.session.add(entrada)
        db.session.flush()
        
        # Actualizar stock del inventario si el producto tiene stock limitado
        if producto and producto.stock_quantity is not None:
            producto.stock_quantity -= checkout_session.cantidad
            if producto.stock_quantity < 0:
                producto.stock_quantity = 0  # No permitir stock negativo
            producto.updated_at = datetime.utcnow()
            logger.info(f"Stock actualizado para {producto.name}: {producto.stock_quantity + checkout_session.cantidad} -> {producto.stock_quantity}")
        
        # Actualizar checkout session
        checkout_session.estado = 'completado'
        checkout_session.completed_at = datetime.utcnow()
        checkout_session.entrada_id = entrada.id
        db.session.commit()
        
        # Enviar email de bienvenida al comprador (con QR y link de pago)
        try:
            from app.helpers.email_ticket_helper import send_resumen_compra_email
            send_resumen_compra_email(entrada)
            logger.info(f"Email de bienvenida enviado a {entrada.comprador_email}")
        except Exception as email_error:
            logger.warning(f"No se pudo enviar email de bienvenida: {email_error}")
        
        # También enviar notificación al admin
        try:
            from app.helpers.email_ticket_helper import send_ticket_email
            send_ticket_email(entrada)
        except Exception as email_error:
            logger.warning(f"No se pudo enviar email de notificación al admin: {email_error}")
        
        # Redirigir a confirmación
        return redirect(url_for('ecommerce.confirmation', ticket_code=entrada.ticket_code))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al procesar pago aprobado: {e}", exc_info=True)
        flash('Error al procesar el pago. Por favor contacta con soporte.', 'error')
        return redirect(url_for('ecommerce.index'))


@ecommerce_bp.route('/payment/callback/<session_id>', methods=['GET', 'POST'])
@exempt_from_csrf
def payment_callback(session_id):
    """
    Callback desde GetNet después del pago
    """
    logger.info(f"Callback recibido: session_id={session_id}")
    logger.info(f"Request args: {dict(request.args)}")
    logger.info(f"Request form: {dict(request.form)}")
    
    checkout_session = CheckoutSession.query.filter_by(session_id=session_id).first()
    
    if not checkout_session:
        logger.error(f"Sesión no encontrada: session_id={session_id}")
        # Intentar buscar sesiones recientes para debug
        from datetime import datetime, timedelta
        desde = datetime.utcnow() - timedelta(minutes=30)
        sesiones_recientes = CheckoutSession.query.filter(
            CheckoutSession.created_at >= desde
        ).order_by(CheckoutSession.created_at.desc()).limit(5).all()
        logger.error(f"Sesiones recientes encontradas: {[s.session_id for s in sesiones_recientes]}")
        flash('Sesión no encontrada', 'error')
        return redirect(url_for('ecommerce.index'))
    
    # Obtener payment_id de parámetros o usar el guardado
    payment_id = (
        request.args.get('payment_id') or 
        request.form.get('payment_id') or 
        request.args.get('paymentId') or
        checkout_session.payment_intent_id
    )
    
    if not payment_id:
        logger.error(f"Callback sin payment_id: session_id={session_id}")
        flash('Error: No se recibió información del pago', 'error')
        return redirect(url_for('ecommerce.index'))
    
    # En modo demo, si el payment_id empieza con DEMO-, simular pago aprobado
    if payment_id and payment_id.startswith('DEMO-'):
        logger.info(f"Modo demo detectado: payment_id={payment_id}")
        # Simular payment_status aprobado para modo demo
        # Estructura compatible con extract_payment_info
        payment_status = {
            'status': 'APPROVED',
            'payment_id': payment_id,
            'requestId': payment_id,
            'transaction_id': f'DEMO-TXN-{payment_id}',
            'auth_code': 'DEMO-AUTH',
            'message': 'Pago simulado en modo demo'
        }
        # Procesar pago aprobado directamente
        logger.info(f"Pago aprobado (demo): payment_id={payment_id}, session_id={session_id}")
        return _process_approved_payment(checkout_session, payment_status)
    
    # Verificar estado del pago con GetNet (solo si no es demo)
    payment_status = get_getnet_payment_status(payment_id)
    
    if not payment_status:
        logger.error(f"No se pudo obtener estado de pago: payment_id={payment_id}")
        flash('Error al verificar el pago. Por favor contacta con soporte.', 'error')
        return redirect(url_for('ecommerce.index'))
    
    # Verificar si el pago está aprobado
    if is_payment_approved(payment_status):
        # Pago aprobado - procesar
        logger.info(f"Pago aprobado: payment_id={payment_id}, session_id={session_id}")
        return _process_approved_payment(checkout_session, payment_status)
    else:
        # Pago rechazado o error
        payment_info = extract_payment_info(payment_status)
        status = payment_info.get('status', 'UNKNOWN')
        
        logger.warning(f"Pago rechazado: payment_id={payment_id}, status={status}")
        
        checkout_session.estado = 'expirado'  # Marcar como expirado para no reutilizar
        db.session.commit()
        
        flash(f'El pago fue {status.lower()}. Por favor intenta nuevamente.', 'error')
        return redirect(url_for('ecommerce.checkout'))


@ecommerce_bp.route('/payment/cancelled/<session_id>')
def payment_cancelled(session_id):
    """Usuario canceló el pago"""
    checkout_session = CheckoutSession.query.filter_by(session_id=session_id).first()
    
    if checkout_session:
        checkout_session.estado = 'expirado'
        db.session.commit()
    
    flash('Pago cancelado', 'info')
    return redirect(url_for('ecommerce.index'))


@ecommerce_bp.route('/confirmation/<ticket_code>')
def confirmation(ticket_code):
    """Página de confirmación con el ticket"""
    entrada = Entrada.query.filter_by(ticket_code=ticket_code).first()
    
    if not entrada:
        flash('Ticket no encontrado', 'error')
        return redirect(url_for('ecommerce.index'))
    
    if entrada.estado_pago != 'pagado':
        flash('Este ticket no está pagado', 'error')
        return redirect(url_for('ecommerce.index'))
    
    # Generar QR code para el ticket
    from app.helpers.qr_ticket_helper import generate_ticket_qr_url
    qr_code = generate_ticket_qr_url(ticket_code)
    
    return render_template('ecommerce/confirmation.html', entrada=entrada, qr_code=qr_code)


@ecommerce_bp.route('/ticket/<ticket_code>')
def view_ticket(ticket_code):
    """Ver ticket (público, para validación)"""
    entrada = Entrada.query.filter_by(ticket_code=ticket_code).first()
    
    if not entrada:
        return jsonify({'error': 'Ticket no encontrado'}), 404
    
    # Generar QR code para el ticket
    from app.helpers.qr_ticket_helper import generate_ticket_qr_url
    qr_code = generate_ticket_qr_url(ticket_code)
    
    return render_template('ecommerce/ticket.html', entrada=entrada, qr_code=qr_code)


@ecommerce_bp.route('/webhook/getnet', methods=['POST'])
@exempt_from_csrf
def getnet_webhook():
    """
    Webhook para recibir notificaciones de GetNet sobre cambios en pagos
    NOTA: Implementar según documentación de GetNet
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Verificar autenticación del webhook (implementar según GetNet)
        # Por ejemplo: verificar firma, token, etc.
        
        payment_id = data.get('payment_id') or data.get('id')
        event_type = data.get('event_type') or data.get('type')
        status = data.get('status')
        
        logger.info(f"Webhook GetNet recibido: payment_id={payment_id}, event_type={event_type}, status={status}")
        
        if not payment_id:
            logger.warning("Webhook sin payment_id")
            return jsonify({'success': False, 'error': 'payment_id requerido'}), 400
        
        # Buscar checkout session por payment_id
        checkout_session = CheckoutSession.query.filter_by(payment_intent_id=payment_id).first()
        
        if not checkout_session:
            logger.warning(f"Checkout session no encontrada para payment_id={payment_id}")
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404
        
        # Si el pago fue aprobado y aún no está procesado
        if status and is_payment_approved({'status': status}):
            if checkout_session.estado != 'completado':
                payment_status = get_getnet_payment_status(payment_id)
                if payment_status and is_payment_approved(payment_status):
                    _process_approved_payment(checkout_session, payment_status)
                    logger.info(f"Pago procesado desde webhook: payment_id={payment_id}")
        
        return jsonify({'success': True, 'message': 'Webhook procesado'})
        
    except Exception as e:
        logger.error(f"Error en webhook GetNet: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

