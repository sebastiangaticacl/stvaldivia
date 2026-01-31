"""
Rutas administrativas para Ecommerce - Gestión de compras y compradores
"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash, Response
from app.models.ecommerce_models import Entrada, CheckoutSession
from app.models.programacion_models import ProgramacionEvento
from app.models import db
from app.helpers.export_utils import DataExporter
from app.helpers.email_ticket_helper import send_resumen_compra_email
from sqlalchemy import func, desc
from datetime import datetime

admin_ecommerce_bp = Blueprint('admin_ecommerce', __name__, url_prefix='/admin/ecommerce')


def require_admin():
    """Verifica que el usuario esté autenticado como admin"""
    if not session.get('admin_logged_in'):
        flash('Debes iniciar sesión como administrador', 'error')
        return redirect(url_for('auth.login_admin'))
    return None


def _build_compras_query():
    """Construye la query de compras aplicando los filtros de la request"""
    # Obtener parámetros de filtrado
    evento_nombre = request.args.get('evento', '')
    estado_pago = request.args.get('estado', '')
    search = request.args.get('search', '')
    
    # Construir query base
    query = Entrada.query
    
    # Filtrar por estado de pago (recibido, pagado, entregado)
    if estado_pago:
        query = query.filter_by(estado_pago=estado_pago)
    
    # Filtrar por evento
    if evento_nombre:
        query = query.filter(Entrada.evento_nombre.ilike(f'%{evento_nombre}%'))
    
    # Buscar por nombre, email o ticket_code
    if search:
        search_filter = db.or_(
            Entrada.comprador_nombre.ilike(f'%{search}%'),
            Entrada.comprador_email.ilike(f'%{search}%'),
            Entrada.ticket_code.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Ordenar por fecha de pago descendente
    query = query.order_by(desc(Entrada.paid_at))
    
    return query


@admin_ecommerce_bp.route('/compras')
def list_compras():
    """Lista de compradores y compras del ecommerce"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    # Obtener parámetros de filtrado
    evento_nombre = request.args.get('evento', '')
    estado_pago = request.args.get('estado', '')
    search = request.args.get('search', '')
    
    # Construir query usando la función auxiliar
    query = _build_compras_query()
    compras = query.all()
    
    # Obtener estadísticas de cupos por evento
    eventos_stats = {}
    eventos = ProgramacionEvento.query.filter(
        ProgramacionEvento.aforo_objetivo.isnot(None)
    ).all()
    
    for evento in eventos:
        entradas_vendidas = db.session.query(
            func.sum(Entrada.cantidad)
        ).filter(
            Entrada.evento_nombre == evento.nombre_evento,
            Entrada.estado_pago.in_(['pagado', 'entregado'])
        ).scalar() or 0
        
        cupos_disponibles = max(0, evento.aforo_objetivo - entradas_vendidas)
        
        eventos_stats[evento.nombre_evento] = {
            'total': evento.aforo_objetivo,
            'vendidos': int(entradas_vendidas),
            'disponibles': int(cupos_disponibles),
            'porcentaje': round((entradas_vendidas / evento.aforo_objetivo * 100), 1) if evento.aforo_objetivo > 0 else 0
        }
    
    # Estadísticas generales (solo pagados y entregados)
    total_compras = Entrada.query.filter(Entrada.estado_pago.in_(['pagado', 'entregado'])).count()
    total_recaudado = db.session.query(
        func.sum(Entrada.precio_total)
    ).filter(Entrada.estado_pago.in_(['pagado', 'entregado'])).scalar() or 0
    
    # Obtener lista de eventos únicos para el filtro
    eventos_disponibles = db.session.query(
        Entrada.evento_nombre
    ).distinct().order_by(Entrada.evento_nombre).all()
    eventos_list = [e[0] for e in eventos_disponibles]
    
    # Agregar función helper para verificar atributos en el template
    def safe_hasattr(obj, attr):
        """Helper para verificar si un objeto tiene un atributo"""
        return hasattr(obj, attr)
    
    return render_template('admin/ecommerce_compras.html',
                         compras=compras,
                         eventos_stats=eventos_stats,
                         total_compras=total_compras,
                         total_recaudado=float(total_recaudado),
                         eventos_list=eventos_list,
                         filtro_evento=evento_nombre,
                         filtro_estado=estado_pago,
                         filtro_search=search,
                         hasattr=safe_hasattr)


@admin_ecommerce_bp.route('/api/stats')
def api_stats():
    """API: Estadísticas de compras del ecommerce"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    # Estadísticas generales (solo pagados y entregados)
    total_compras = Entrada.query.filter(Entrada.estado_pago.in_(['pagado', 'entregado'])).count()
    total_recaudado = db.session.query(
        func.sum(Entrada.precio_total)
    ).filter(Entrada.estado_pago.in_(['pagado', 'entregado'])).scalar() or 0
    
    # Estadísticas por evento
    eventos_stats = {}
    eventos = ProgramacionEvento.query.filter(
        ProgramacionEvento.aforo_objetivo.isnot(None)
    ).all()
    
    for evento in eventos:
        entradas_vendidas = db.session.query(
            func.sum(Entrada.cantidad)
        ).filter(
            Entrada.evento_nombre == evento.nombre_evento,
            Entrada.estado_pago.in_(['pagado', 'entregado'])
        ).scalar() or 0
        
        cupos_disponibles = max(0, evento.aforo_objetivo - entradas_vendidas)
        
        eventos_stats[evento.nombre_evento] = {
            'total': evento.aforo_objetivo,
            'vendidos': int(entradas_vendidas),
            'disponibles': int(cupos_disponibles),
            'porcentaje': round((entradas_vendidas / evento.aforo_objetivo * 100), 1) if evento.aforo_objetivo > 0 else 0
        }
    
    return jsonify({
        'total_compras': total_compras,
        'total_recaudado': float(total_recaudado),
        'eventos_stats': eventos_stats
    })


@admin_ecommerce_bp.route('/compras/cambiar-estado-masivo', methods=['POST'])
def cambiar_estado_masivo():
    """API: Cambiar el estado de múltiples pedidos"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        entrada_ids = data.get('entrada_ids', [])
        nuevo_estado = data.get('estado', '').lower()
        
        if not entrada_ids:
            return jsonify({
                'success': False,
                'error': 'No se seleccionaron pedidos'
            }), 400
        
        # Validar estado
        estados_validos = ['recibido', 'pagado', 'entregado']
        if nuevo_estado not in estados_validos:
            return jsonify({
                'success': False,
                'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
            }), 400
        
        # Buscar las entradas
        entradas = Entrada.query.filter(Entrada.id.in_(entrada_ids)).all()
        
        if not entradas:
            return jsonify({
                'success': False,
                'error': 'No se encontraron pedidos con los IDs proporcionados'
            }), 404
        
        # Actualizar cada entrada
        actualizados = 0
        for entrada in entradas:
            entrada.estado_pago = nuevo_estado
            
            # Actualizar timestamps según el estado
            if nuevo_estado == 'pagado' and not entrada.paid_at:
                entrada.paid_at = datetime.utcnow()
            elif nuevo_estado == 'entregado' and not entrada.paid_at:
                entrada.paid_at = datetime.utcnow()
            
            actualizados += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Se actualizaron {actualizados} pedido(s) a estado {nuevo_estado}',
            'actualizados': actualizados,
            'nuevo_estado': nuevo_estado
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al cambiar estados: {str(e)}'
        }), 500


@admin_ecommerce_bp.route('/compras/<int:entrada_id>/cambiar-estado', methods=['POST'])
def cambiar_estado_pedido(entrada_id):
    """API: Cambiar el estado de un pedido"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado', '').lower()
        
        # Validar estado
        estados_validos = ['recibido', 'pagado', 'entregado']
        if nuevo_estado not in estados_validos:
            return jsonify({
                'success': False,
                'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
            }), 400
        
        # Buscar la entrada
        entrada = Entrada.query.get_or_404(entrada_id)
        
        # Guardar estado anterior
        estado_anterior = entrada.estado_pago
        
        # Actualizar estado
        entrada.estado_pago = nuevo_estado
        
        # Actualizar timestamps según el estado
        if nuevo_estado == 'pagado' and not entrada.paid_at:
            entrada.paid_at = datetime.utcnow()
        elif nuevo_estado == 'entregado' and not entrada.paid_at:
            # Si se marca como entregado sin estar pagado, también marcar como pagado
            entrada.paid_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Estado cambiado de {estado_anterior} a {nuevo_estado}',
            'nuevo_estado': nuevo_estado,
            'estado_anterior': estado_anterior
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al cambiar estado: {str(e)}'
        }), 500


@admin_ecommerce_bp.route('/compras/export')
def export_compras():
    """Exporta las compras del ecommerce a CSV"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    try:
        # Construir query usando la función auxiliar
        query = _build_compras_query()
        compras = query.all()
        
        if not compras:
            flash('No hay compras para exportar con los filtros seleccionados', 'warning')
            return redirect(url_for('admin_ecommerce.list_compras'))
        
        # Preparar datos para exportación
        export_data = []
        for compra in compras:
            export_data.append({
                'Ticket Code': compra.ticket_code,
                'Comprador': compra.comprador_nombre,
                'Email': compra.comprador_email,
                'RUT': compra.comprador_rut or '',
                'Teléfono': compra.comprador_telefono or '',
                'Evento': compra.evento_nombre,
                'Fecha Evento': compra.evento_fecha.strftime('%d/%m/%Y %H:%M') if compra.evento_fecha else '',
                'Lugar': compra.evento_lugar or '',
                'Cantidad': compra.cantidad,
                'Precio Unitario': float(compra.precio_unitario) if compra.precio_unitario else 0.0,
                'Precio Total': float(compra.precio_total) if compra.precio_total else 0.0,
                'Estado Pago': compra.estado_pago,
                'Método Pago': compra.metodo_pago or '',
                'GetNet Payment ID': compra.getnet_payment_id or '',
                'GetNet Transaction ID': compra.getnet_transaction_id or '',
                'GetNet Auth Code': compra.getnet_auth_code or '',
                'Fecha Creación': compra.created_at.strftime('%d/%m/%Y %H:%M:%S') if compra.created_at else '',
                'Fecha Pago': compra.paid_at.strftime('%d/%m/%Y %H:%M:%S') if compra.paid_at else '',
                'Fecha Cancelación': compra.cancelled_at.strftime('%d/%m/%Y %H:%M:%S') if compra.cancelled_at else ''
            })
        
        # Exportar usando DataExporter
        return DataExporter.export_to_csv(export_data, "compras_ecommerce")
        
    except Exception as e:
        flash(f'Error al exportar compras: {str(e)}', 'error')
        return redirect(url_for('admin_ecommerce.list_compras'))


@admin_ecommerce_bp.route('/compras/<int:entrada_id>/preview-email', methods=['GET'])
def preview_resumen_compra(entrada_id):
    """Vista previa del email de resumen de compra"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    try:
        # Buscar la entrada
        entrada = Entrada.query.get_or_404(entrada_id)
        
        # Generar HTML del email
        from app.helpers.email_ticket_helper import generate_resumen_compra_html
        email_subject, email_body = generate_resumen_compra_html(entrada, preview=True)
        
        # Calcular precio total para mostrar info
        precio_total = float(entrada.cantidad) * float(entrada.precio_unitario) if entrada.precio_unitario else float(entrada.precio_total or 0)
        from app.helpers.email_ticket_helper import get_payment_link_by_amount
        payment_link = get_payment_link_by_amount(precio_total)
        
        # Verificar si se mostrará QR (solo si está pagado o entregado)
        mostrar_qr = entrada.estado_pago.lower() in ['pagado', 'entregado']
        
        return render_template('admin/preview_email.html',
                             entrada=entrada,
                             email_subject=email_subject,
                             email_body=email_body,
                             precio_total=precio_total,
                             payment_link=payment_link,
                             mostrar_qr=mostrar_qr)
        
    except Exception as e:
        flash(f'Error al generar vista previa: {str(e)}', 'error')
        return redirect(url_for('admin_ecommerce.list_compras'))


@admin_ecommerce_bp.route('/compras/<int:entrada_id>/enviar-resumen', methods=['POST'])
def enviar_resumen_compra(entrada_id):
    """API: Enviar resumen de compra por email al comprador"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        # Buscar la entrada
        entrada = Entrada.query.get_or_404(entrada_id)
        
        if not entrada.comprador_email:
            return jsonify({
                'success': False,
                'error': 'El pedido no tiene email del comprador'
            }), 400
        
        # Verificar configuración SMTP antes de intentar enviar
        import os
        from flask import current_app
        smtp_server = current_app.config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER')
        smtp_user = current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER')
        smtp_password = current_app.config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')
        
        if not all([smtp_server, smtp_user, smtp_password]):
            logger.warning(f"SMTP config missing: server={bool(smtp_server)}, user={bool(smtp_user)}, password={bool(smtp_password)}")
            return jsonify({
                'success': False,
                'error': 'Configuración SMTP incompleta. Verifica SMTP_SERVER, SMTP_USER y SMTP_PASSWORD en las variables de entorno.'
            }), 500
        
        # Enviar email con captura de excepciones para mejor diagnóstico
        try:
            enviado = send_resumen_compra_email(entrada)
        except Exception as send_error:
            logger.error(f"Error al llamar send_resumen_compra_email: {send_error}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Error al enviar email: {str(send_error)}'
            }), 500
        
        # Recargar la entrada para obtener los campos actualizados
        db.session.refresh(entrada)
        
        if enviado:
            fecha_envio = None
            email_enviado = False
            if hasattr(entrada, 'email_resumen_enviado_at') and entrada.email_resumen_enviado_at:
                fecha_envio = entrada.email_resumen_enviado_at.strftime('%d/%m/%Y %H:%M')
            if hasattr(entrada, 'email_resumen_enviado'):
                email_enviado = entrada.email_resumen_enviado
            
            return jsonify({
                'success': True,
                'message': f'Resumen enviado exitosamente a {entrada.comprador_email}',
                'email': entrada.comprador_email,
                'fecha_envio': fecha_envio or 'N/A',
                'email_enviado': email_enviado
            })
        else:
            # Obtener último error de logs si es posible
            error_msg = 'No se pudo enviar el email. Verifica la configuración SMTP (SMTP_SERVER, SMTP_USER, SMTP_PASSWORD) y los logs del servidor.'
            return jsonify({
                'success': False,
                'error': error_msg,
                'email_enviado': entrada.email_resumen_enviado if hasattr(entrada, 'email_resumen_enviado') else False
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al enviar resumen: {str(e)}'
        }), 500


@admin_ecommerce_bp.route('/compras/enviar-resumen-por-codigo', methods=['POST'])
def enviar_resumen_por_codigo():
    """API: Enviar resumen de compra por email usando ticket_code"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        ticket_code = data.get('ticket_code') if data else request.form.get('ticket_code')
        
        if not ticket_code:
            return jsonify({
                'success': False,
                'error': 'Se requiere el parámetro ticket_code'
            }), 400
        
        # Buscar la entrada por ticket_code
        entrada = Entrada.query.filter_by(ticket_code=ticket_code).first()
        
        if not entrada:
            return jsonify({
                'success': False,
                'error': f'No se encontró la entrada con código: {ticket_code}'
            }), 404
        
        if not entrada.comprador_email:
            return jsonify({
                'success': False,
                'error': 'El pedido no tiene email del comprador'
            }), 400
        
        # Enviar email
        enviado = send_resumen_compra_email(entrada)
        
        # Recargar la entrada para obtener los campos actualizados
        db.session.refresh(entrada)
        
        if enviado:
            fecha_envio = None
            email_enviado = False
            if hasattr(entrada, 'email_resumen_enviado_at') and entrada.email_resumen_enviado_at:
                fecha_envio = entrada.email_resumen_enviado_at.strftime('%d/%m/%Y %H:%M')
            if hasattr(entrada, 'email_resumen_enviado'):
                email_enviado = entrada.email_resumen_enviado
            
            return jsonify({
                'success': True,
                'message': f'Resumen enviado exitosamente a {entrada.comprador_email}',
                'email': entrada.comprador_email,
                'fecha_envio': fecha_envio or 'N/A',
                'email_enviado': email_enviado,
                'ticket_code': ticket_code
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo enviar el email. Verifica la configuración SMTP.',
                'email_enviado': entrada.email_resumen_enviado if hasattr(entrada, 'email_resumen_enviado') else False
            }), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al enviar resumen: {str(e)}'
        }), 500


@admin_ecommerce_bp.route('/compras/cambiar-todos-a-recibido', methods=['POST'])
def cambiar_todos_a_recibido():
    """API: Cambiar todos los estados a 'recibido'"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        # Obtener todas las entradas
        entradas = Entrada.query.all()
        
        if not entradas:
            return jsonify({
                'success': False,
                'error': 'No hay compras en la base de datos'
            }), 400
        
        # Contar estados actuales
        estados_antes = {}
        for entrada in entradas:
            estado = entrada.estado_pago or 'sin_estado'
            estados_antes[estado] = estados_antes.get(estado, 0) + 1
        
        # Cambiar todos los estados a 'recibido'
        actualizados = 0
        for entrada in entradas:
            if entrada.estado_pago != 'recibido':
                entrada.estado_pago = 'recibido'
                # Si tenía paid_at, limpiarlo ya que ahora está en 'recibido'
                if entrada.paid_at:
                    entrada.paid_at = None
                actualizados += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Se actualizaron {actualizados} compras a estado "recibido"',
            'actualizados': actualizados,
            'total': len(entradas),
            'estados_antes': estados_antes
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al cambiar estados: {str(e)}'
        }), 500


@admin_ecommerce_bp.route('/compras/test-smtp', methods=['POST'])
def test_smtp():
    """API: Probar conexión SMTP"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        import os
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from flask import current_app
        
        smtp_server = current_app.config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER')
        smtp_port = int(current_app.config.get('SMTP_PORT') or os.environ.get('SMTP_PORT', '587'))
        smtp_user = current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER')
        smtp_password = current_app.config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')
        smtp_from = current_app.config.get('SMTP_FROM') or os.environ.get('SMTP_FROM') or smtp_user
        
        if not all([smtp_server, smtp_user, smtp_password]):
            return jsonify({
                'success': False,
                'error': 'Configuración SMTP incompleta',
                'config': {'server': bool(smtp_server), 'port': smtp_port, 'user': bool(smtp_user), 'password': bool(smtp_password)}
            }), 500
        
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
            
            server.login(smtp_user, smtp_password)
            msg = MIMEMultipart()
            msg['From'] = smtp_from
            msg['To'] = smtp_user
            msg['Subject'] = 'Prueba SMTP'
            msg.attach(MIMEText('Prueba de configuración SMTP.', 'plain'))
            server.send_message(msg)
            server.quit()
            
            return jsonify({
                'success': True,
                'message': f'Conexión SMTP exitosa. Email enviado a {smtp_user}',
                'config': {'server': smtp_server, 'port': smtp_port, 'user': smtp_user}
            })
        except smtplib.SMTPAuthenticationError as e:
            return jsonify({
                'success': False,
                'error': f'Error de autenticación: {str(e)}',
                'config': {'server': smtp_server, 'port': smtp_port, 'user': smtp_user},
                'suggestion': 'Verifica credenciales y que la cuenta esté activa'
            }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error: {str(e)}',
                'config': {'server': smtp_server, 'port': smtp_port, 'user': smtp_user}
            }), 500
    except Exception as e:
        logger.error(f"Error en test SMTP: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500
