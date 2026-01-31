"""
Helper para envío de emails con tickets de entrada
"""
import logging
import os
from typing import Optional
from datetime import datetime
from flask import current_app, url_for
from app.models.ecommerce_models import Entrada

logger = logging.getLogger(__name__)


def send_ticket_email(entrada: Entrada) -> bool:
    """
    Envía email con el ticket de entrada al comprador
    
    Args:
        entrada: Objeto Entrada a enviar
        
    Returns:
        True si se envió exitosamente, False en caso contrario
    """
    # MODO SOLO LOCAL: no enviar emails ni conectar a SMTP
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            logger.info("LOCAL_ONLY activo: email de ticket no enviado (send_ticket_email)")
            return False
    except Exception:
        pass

    try:
        # Verificar si hay configuración de email
        # Por ahora solo loguear, implementar envío real cuando haya SMTP configurado
        email_subject = f"Nueva compra: {entrada.evento_nombre} - {entrada.comprador_nombre}"
        
        # Generar URL del ticket (manejar caso fuera de request)
        try:
            ticket_url = url_for('ecommerce.view_ticket', ticket_code=entrada.ticket_code, _external=True)
        except RuntimeError:
            # Si no hay request activo, construir URL manualmente
            public_base_url = current_app.config.get('PUBLIC_BASE_URL') or os.environ.get('PUBLIC_BASE_URL')
            if public_base_url:
                ticket_url = f"{public_base_url.rstrip('/')}/ecommerce/ticket/{entrada.ticket_code}"
            else:
                ticket_url = f"/ecommerce/ticket/{entrada.ticket_code}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #667eea;">¡Gracias por tu compra!</h2>
            
            <p>Hola,</p>
            
            <p>Se ha recibido una nueva compra de <strong>{entrada.comprador_nombre}</strong> ({entrada.comprador_email}).</p>
            <p>Aquí están los detalles de la entrada:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <h3 style="margin-top: 0;">{entrada.evento_nombre}</h3>
                <p style="font-size: 24px; font-weight: bold; letter-spacing: 3px; color: #333;">
                    {entrada.ticket_code}
                </p>
            </div>
            
            <div style="margin: 20px 0;">
                <p><strong>Comprador:</strong> {entrada.comprador_nombre}</p>
                <p><strong>Email del comprador:</strong> {entrada.comprador_email}</p>
                <p><strong>Teléfono:</strong> {entrada.comprador_telefono if entrada.comprador_telefono else 'No proporcionado'}</p>
                <p><strong>RUT:</strong> {entrada.comprador_rut if entrada.comprador_rut else 'No proporcionado'}</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
                <p><strong>Fecha del evento:</strong> {entrada.evento_fecha.strftime('%d/%m/%Y %H:%M') if entrada.evento_fecha else 'N/A'}</p>
                {f'<p><strong>Lugar:</strong> {entrada.evento_lugar}</p>' if entrada.evento_lugar else ''}
                <p><strong>Cantidad:</strong> {entrada.cantidad} entrada(s)</p>
                <p><strong>Total pagado:</strong> ${entrada.precio_total:,.0f}</p>
            </div>
            
            <div style="margin: 30px 0; text-align: center;">
                <a href="{ticket_url}" 
                   style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    Ver mi Ticket
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Presenta este ticket en la entrada del evento. También puedes mostrarlo desde tu teléfono.
            </p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="color: #999; font-size: 12px;">
                Si tienes alguna pregunta, por favor contacta con nosotros.
            </p>
        </body>
        </html>
        """
        
        # Enviar email usando smtplib (estándar de Python)
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Obtener configuración de email desde variables de entorno
        smtp_server = current_app.config.get('SMTP_SERVER') or os.environ.get('SMTP_SERVER')
        smtp_port = int(current_app.config.get('SMTP_PORT') or os.environ.get('SMTP_PORT', '587'))
        smtp_user = current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER')
        smtp_password = current_app.config.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')
        smtp_from = current_app.config.get('SMTP_FROM') or os.environ.get('SMTP_FROM') or smtp_user
        
        if not smtp_server or not smtp_user or not smtp_password:
            logger.warning("⚠️ Configuración de SMTP incompleta. Email no enviado.")
            logger.info(f"📧 Email de ticket preparado para {entrada.comprador_email} (no enviado)")
            logger.debug(f"Subject: {email_subject}")
            logger.debug(f"Ticket URL: {ticket_url}")
            return False
        
        try:
            # Crear mensaje
            # Siempre enviar a hola@valdiviaesbimba.cl
            email_destino = 'hola@valdiviaesbimba.cl'
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_subject
            msg['From'] = smtp_from
            msg['To'] = email_destino
            # Incluir el email del comprador en el cuerpo del mensaje para referencia
            
            # Agregar cuerpo HTML
            html_part = MIMEText(email_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Conectar y enviar
            if smtp_port == 465:
                # SSL
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                # TLS
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email enviado exitosamente a {email_destino} (comprador: {entrada.comprador_email})")
            return True
            
        except Exception as email_error:
            logger.error(f"❌ Error al enviar email a hola@valdiviaesbimba.cl: {email_error}", exc_info=True)
            # No fallar la compra si el email falla
            return False
        
    except Exception as e:
        logger.error(f"Error al enviar email de ticket: {e}", exc_info=True)
        return False


def get_payment_link_by_amount(monto: float) -> str:
    """
    Obtiene el link de pago según el monto de la compra
    
    Args:
        monto: Monto total de la compra
        
    Returns:
        URL del link de pago correspondiente
    """
    # Links de pago SumUp según monto
    payment_links = {
        5000: 'https://pay.sumup.com/b2c/Q3XX3AP6',
        10000: 'https://pay.sumup.com/b2c/Q877B989',
        15000: 'https://pay.sumup.com/b2c/QV9H60YE',
        20000: 'https://pay.sumup.com/b2c/QWXAE7H2'
    }
    
    # Redondear al monto más cercano
    monto_redondeado = round(monto / 1000) * 1000
    
    # Buscar el link correspondiente (usar el más cercano hacia abajo)
    if monto_redondeado >= 20000:
        return payment_links[20000]
    elif monto_redondeado >= 15000:
        return payment_links[15000]
    elif monto_redondeado >= 10000:
        return payment_links[10000]
    elif monto_redondeado >= 5000:
        return payment_links[5000]
    else:
        # Si es menor a $5.000, usar el link de $5.000
        return payment_links[5000]


def generate_resumen_compra_html(entrada: Entrada, preview: bool = False) -> tuple[str, str]:
    """
    Genera el HTML del email de resumen de compra
    
    Args:
        entrada: Objeto Entrada
        preview: Si es True, no incluye información sensible
        
    Returns:
        Tupla con (subject, html_body)
    """
    from app.helpers.qr_ticket_helper import generate_ticket_qr
    
    email_subject = f"Resumen de tu compra - {entrada.evento_nombre}"
    
    # Generar URL del ticket
    try:
        ticket_url = url_for('ecommerce.view_ticket', ticket_code=entrada.ticket_code, _external=True)
    except RuntimeError:
        public_base_url = current_app.config.get('PUBLIC_BASE_URL') or os.environ.get('PUBLIC_BASE_URL')
        if public_base_url:
            ticket_url = f"{public_base_url.rstrip('/')}/ecommerce/ticket/{entrada.ticket_code}"
        else:
            ticket_url = f"/ecommerce/ticket/{entrada.ticket_code}"
    
    # Formatear fechas
    if entrada.evento_fecha:
        # Usar la fecha del evento pero siempre mostrar 23:59 como hora
        fecha_evento = entrada.evento_fecha.strftime('%d de %B de %Y a las 23:59')
    else:
        fecha_evento = 'No especificada'
    fecha_compra = entrada.created_at.strftime('%d/%m/%Y %H:%M') if entrada.created_at else 'N/A'
    fecha_pago = entrada.paid_at.strftime('%d/%m/%Y %H:%M') if entrada.paid_at else 'N/A'
    
    # Calcular precio total
    precio_total = float(entrada.cantidad) * float(entrada.precio_unitario) if entrada.precio_unitario else float(entrada.precio_total or 0)
    
    # Obtener link de pago según el monto (usar el link correcto según el monto)
    payment_link = get_payment_link_by_amount(precio_total)
    
    # Estado en español
    estados = {
        'recibido': 'Pendiente de pago',
        'pagado': 'Pagado',
        'entregado': 'Entregado'
    }
    estado_display = estados.get(entrada.estado_pago.lower(), entrada.estado_pago.title())
    
    # Método de pago en español
    metodos_pago = {
        'getnet_web': 'Tarjeta de Crédito/Débito (GetNet)',
        'getnet_link': 'Link de Pago (GetNet)',
        'manual': 'Pago Manual',
        'sumup': 'Link de Pago (SumUp)'
    }
    metodo_display = metodos_pago.get(entrada.metodo_pago, entrada.metodo_pago or 'No especificado')
    
    # Determinar si mostrar link de pago (siempre mostrar si el estado es "recibido" o si el método es "manual" o si no está pagado)
    estado_lower = entrada.estado_pago.lower() if entrada.estado_pago else ''
    mostrar_link_pago = estado_lower == 'recibido' or entrada.metodo_pago == 'manual' or estado_lower not in ['pagado', 'entregado']
    
    # Generar QR siempre (se incluye en todos los emails)
    # El QR se mostrará pero con mensaje indicando que solo se activa cuando se recibe el pago
    qr_code_base64 = generate_ticket_qr(entrada.ticket_code, size=250)
    mostrar_qr = qr_code_base64 is not None
    
    # Determinar si el pago está realizado (para mostrar mensaje diferente en el QR)
    # No mostrar "pago verificado" si el método de pago es manual
    pago_realizado = entrada.estado_pago.lower() in ['pagado', 'entregado'] and entrada.metodo_pago != 'manual'
    
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 0; background-color: #ffffff;">
        
        <div style="background: white; padding: 30px; border-radius: 0; box-shadow: none; border: none;">
            
            <h1 style="color: #333; margin-top: 0; font-size: 24px;">¡Gracias por querer ser parte de nuestra fiesta! 🎉</h1>
            
            <p style="font-size: 16px; margin-bottom: 25px;">Hola <strong>{entrada.comprador_nombre}</strong>,</p>
            
            <p style="font-size: 16px; color: #666; margin-bottom: 25px;">
                Te adjuntamos el link de pago y el código QR que deberás presentar junto con tu cédula de identidad el día del evento. 
                El código QR solo se activa cuando se recibe el pago.
            </p>
            
            <!-- Link de Pago -->
            {f'''
            <div style="text-align: center; margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%); border-radius: 12px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);">
                <h2 style="color: white; margin-top: 0; font-size: 24px; margin-bottom: 15px;">💳 Link de Pago</h2>
                <a href="{payment_link}" 
                   target="_blank"
                   style="background: white; color: #f59e0b; padding: 18px 40px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 700; font-size: 20px; margin: 15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                    💰 Pagar ${precio_total:,.0f}
                </a>
                <p style="color: rgba(255,255,255,0.95); font-size: 16px; margin: 20px 0 10px 0; font-weight: 500;">
                    <a href="{payment_link}" target="_blank" style="color: white; text-decoration: underline;">Haz clic aquí para realizar tu pago</a>
                </p>
                <p style="color: rgba(255,255,255,0.85); font-size: 14px; margin: 10px 0 0 0;">
                    <a href="{payment_link}" target="_blank" style="color: white; word-break: break-all; text-decoration: underline;">{payment_link}</a>
                </p>
            </div>
            ''' if mostrar_link_pago else ''}
            
            <!-- Código QR -->
            {f'''
            <div style="text-align: center; margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 8px;">
                <h2 style="color: #333; margin-top: 0; font-size: 18px;">Código QR</h2>
                <img src="cid:qr_{entrada.ticket_code}" 
                     alt="Código QR - Ticket {entrada.ticket_code}" 
                     style="width: 200px; height: 200px; display: block; margin: 15px auto; background: white; padding: 10px; border-radius: 8px;" />
                <p style="color: #666; font-size: 14px; margin: 15px 0 0 0;">
                    {'✓ Pago verificado - QR activo' if pago_realizado else '⏳ Pendiente de pago - Se activará al recibir el pago'}
                </p>
            </div>
            ''' if mostrar_qr and qr_code_base64 else ''}
            
            <!-- Información -->
            <div style="margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 8px;">
                <h2 style="color: #333; margin-top: 0; font-size: 18px;">Información</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Evento:</strong></td>
                        <td style="padding: 8px 0; color: #333;">{entrada.evento_nombre}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Fecha:</strong></td>
                        <td style="padding: 8px 0; color: #333;">{fecha_evento}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Cantidad:</strong></td>
                        <td style="padding: 8px 0; color: #333;">{entrada.cantidad} entrada(s)</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Total:</strong></td>
                        <td style="padding: 8px 0; color: #333; font-weight: bold;">${precio_total:,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Estado:</strong></td>
                        <td style="padding: 8px 0; color: #333;">{estado_display}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666;"><strong>Ticket:</strong></td>
                        <td style="padding: 8px 0; color: #333; font-family: monospace;">{entrada.ticket_code}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Instrucciones -->
            <div style="margin: 30px 0; padding: 15px; background: #e7f3ff; border-left: 4px solid #2196F3; border-radius: 4px;">
                <p style="margin: 0; color: #1976D2; font-size: 14px;">
                    <strong>Importante:</strong> Presenta el código QR junto con tu cédula de identidad el día del evento. 
                    Puedes mostrarlo desde tu teléfono o imprimirlo.
                </p>
            </div>
            
        </div>
        
        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p style="margin: 5px 0;">Club Bimba Valdivia</p>
            <p style="margin: 5px 0;">hola@valdiviaesbimba.cl</p>
        </div>
        
    </body>
    </html>
    """
    
    return email_subject, email_body


def send_resumen_compra_email(entrada: Entrada) -> bool:
    """
    Envía email con resumen de compra y datos de pago directamente al comprador
    
    Args:
        entrada: Objeto Entrada a enviar
        
    Returns:
        True si se envió exitosamente, False en caso contrario
    """
    # MODO SOLO LOCAL: no enviar emails ni conectar a SMTP
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            logger.info("LOCAL_ONLY activo: email de resumen no enviado (send_resumen_compra_email)")
            return False
    except Exception:
        pass

    try:
        if not entrada.comprador_email:
            logger.warning(f"⚠️ No hay email del comprador para entrada {entrada.ticket_code}")
            return False
        
        email_subject = f"Resumen de tu compra - {entrada.evento_nombre}"
        
        # Generar URL del ticket
        try:
            ticket_url = url_for('ecommerce.view_ticket', ticket_code=entrada.ticket_code, _external=True)
        except RuntimeError:
            public_base_url = current_app.config.get('PUBLIC_BASE_URL') or os.environ.get('PUBLIC_BASE_URL')
            if public_base_url:
                ticket_url = f"{public_base_url.rstrip('/')}/ecommerce/ticket/{entrada.ticket_code}"
            else:
                ticket_url = f"/ecommerce/ticket/{entrada.ticket_code}"
        
        # Formatear fechas
        fecha_evento = entrada.evento_fecha.strftime('%d de %B de %Y a las %H:%M') if entrada.evento_fecha else 'No especificada'
        fecha_compra = entrada.created_at.strftime('%d/%m/%Y %H:%M') if entrada.created_at else 'N/A'
        fecha_pago = entrada.paid_at.strftime('%d/%m/%Y %H:%M') if entrada.paid_at else 'N/A'
        
        # Generar HTML del email usando la función helper
        email_subject, email_body = generate_resumen_compra_html(entrada, preview=False)
        
        # Enviar email usando smtplib
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Obtener configuración de email
        # Priorizar variables de entorno del sistema (desde systemd)
        smtp_server = os.environ.get('SMTP_SERVER') or current_app.config.get('SMTP_SERVER')
        # Por defecto usar puerto 587 (TLS) en lugar de 465 (SSL)
        smtp_port = int(os.environ.get('SMTP_PORT') or current_app.config.get('SMTP_PORT') or '587')
        smtp_user = os.environ.get('SMTP_USER') or current_app.config.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD') or current_app.config.get('SMTP_PASSWORD')
        smtp_from = os.environ.get('SMTP_FROM') or current_app.config.get('SMTP_FROM') or smtp_user
        
        # Log de configuración (sin mostrar contraseña completa)
        logger.info(f"📧 Configuración SMTP: servidor={smtp_server}, puerto={smtp_port}, usuario={smtp_user}")
        logger.info(f"   Variables desde os.environ: SMTP_SERVER={bool(os.environ.get('SMTP_SERVER'))}, SMTP_USER={bool(os.environ.get('SMTP_USER'))}, SMTP_PASSWORD={bool(os.environ.get('SMTP_PASSWORD'))}")
        logger.info(f"   Variables desde current_app.config: SMTP_SERVER={bool(current_app.config.get('SMTP_SERVER'))}, SMTP_USER={bool(current_app.config.get('SMTP_USER'))}, SMTP_PASSWORD={bool(current_app.config.get('SMTP_PASSWORD'))}")
        
        if not smtp_server or not smtp_user or not smtp_password:
            logger.error("❌ Configuración de SMTP incompleta. Email no enviado.")
            logger.error(f"   SMTP_SERVER: {smtp_server} (tipo: {type(smtp_server)})")
            logger.error(f"   SMTP_USER: {smtp_user} (tipo: {type(smtp_user)})")
            logger.error(f"   SMTP_PASSWORD: {'***' if smtp_password else 'None'} (tipo: {type(smtp_password)})")
            logger.error(f"   Variables de entorno disponibles: {[k for k in os.environ.keys() if 'SMTP' in k]}")
            logger.info(f"📧 Email de resumen preparado para {entrada.comprador_email} (no enviado)")
            return False
        
        try:
            # Crear mensaje - ENVIAR AL COMPRADOR
            msg = MIMEMultipart('related')  # Cambiar a 'related' para permitir attachments inline
            msg['Subject'] = email_subject
            # Usar nombre del remitente más amigable
            msg['From'] = f"Club Bimba Valdivia <{smtp_from}>"
            msg['To'] = entrada.comprador_email
            
            # Agregar cuerpo HTML
            html_part = MIMEText(email_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Adjuntar QR como imagen para mejor compatibilidad con clientes de email
            # (algunos bloquean imágenes base64 inline)
            from app.helpers.qr_ticket_helper import generate_ticket_qr
            import base64
            qr_code_base64 = generate_ticket_qr(entrada.ticket_code, size=250)
            if qr_code_base64:
                try:
                    # Extraer los datos base64 del data URI
                    if qr_code_base64.startswith('data:image'):
                        base64_data = qr_code_base64.split(',')[1]
                    else:
                        base64_data = qr_code_base64
                    
                    # Decodificar y crear attachment
                    qr_image_data = base64.b64decode(base64_data)
                    from email.mime.image import MIMEImage
                    qr_attachment = MIMEImage(qr_image_data)
                    qr_cid = f'qr_{entrada.ticket_code}'
                    qr_attachment.add_header('Content-ID', f'<{qr_cid}>')
                    qr_attachment.add_header('Content-Disposition', 'inline', filename=f'qr_{entrada.ticket_code}.png')
                    msg.attach(qr_attachment)
                    logger.info(f"   ✅ QR adjuntado como imagen (Content-ID: {qr_cid})")
                except Exception as qr_error:
                    logger.warning(f"   ⚠️ No se pudo adjuntar QR como imagen: {qr_error}")
            
            # Conectar y enviar
            # Si el servidor es una IP, usarla directamente. Si es un hostname, resolver DNS primero
            import socket
            import re
            
            # Verificar si es una IP (formato IPv4)
            ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
            if ip_pattern.match(smtp_server):
                # Es una IP, usarla directamente (evita problemas de DNS con eventlet/greendns)
                smtp_host = smtp_server
                logger.info(f"🔌 Usando IP directa: {smtp_host}")
            else:
                # Es un hostname, resolver DNS antes de conectar para evitar problemas con eventlet/greendns
                try:
                    logger.info(f"🔍 Resolviendo DNS para {smtp_server}...")
                    # Usar socket estándar (no eventlet) para resolver DNS
                    # Esto evita el timeout de greendns
                    smtp_ip = socket.gethostbyname(smtp_server)
                    logger.info(f"   ✅ DNS resuelto: {smtp_server} -> {smtp_ip}")
                    # Usar IP directamente para evitar problemas con greendns
                    smtp_host = smtp_ip
                except Exception as dns_error:
                    logger.warning(f"   ⚠️ No se pudo resolver DNS, usando hostname: {dns_error}")
                    smtp_host = smtp_server
            
            logger.info(f"🔌 Conectando a SMTP: {smtp_host}:{smtp_port}")
            logger.info(f"   Usuario: {smtp_user}")
            
            try:
                if smtp_port == 465:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
                    logger.info("   ✅ Conexión SSL establecida")
                else:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                    server.starttls()
                    logger.info("   ✅ TLS iniciado")
                
                # Intentar autenticación
                logger.info(f"🔐 Intentando autenticación con usuario: {smtp_user}")
                server.login(smtp_user, smtp_password)
                logger.info("   ✅ Autenticación SMTP exitosa")
            except Exception as conn_error:
                logger.error(f"   ❌ Error en conexión/autenticación: {type(conn_error).__name__}: {str(conn_error)}")
                raise
            server.send_message(msg)
            server.quit()
            
            # Marcar como enviado en la base de datos
            from app.models import db
            entrada.email_resumen_enviado = True
            entrada.email_resumen_enviado_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"✅ Email de resumen enviado exitosamente a {entrada.comprador_email} (Ticket: {entrada.ticket_code})")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = str(e)
            logger.error(f"❌ Error de autenticación SMTP: {error_msg}")
            logger.error(f"   Servidor: {smtp_server}:{smtp_port}")
            logger.error(f"   Usuario: {smtp_user}")
            logger.error(f"   Verifica que las credenciales sean correctas y que la cuenta esté activa")
            return False
        except smtplib.SMTPException as e:
            error_msg = str(e)
            logger.error(f"❌ Error SMTP: {error_msg}")
            logger.error(f"   Servidor: {smtp_server}:{smtp_port}")
            return False
        except Exception as email_error:
            error_msg = str(email_error)
            logger.error(f"❌ Error al enviar email de resumen a {entrada.comprador_email}: {error_msg}", exc_info=True)
            return False
        
    except Exception as e:
        logger.error(f"Error al enviar email de resumen: {e}", exc_info=True)
        return False

