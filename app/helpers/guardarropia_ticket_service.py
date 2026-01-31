"""
Servicio para generar y gestionar Tickets QR de Guardarropía
FASE 3: Generación automática de tickets QR al depositar prenda
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from flask import current_app
from app.models import db
from app.models.guardarropia_ticket_models import GuardarropiaTicket, GuardarropiaTicketLog
from app.models.guardarropia_models import GuardarropiaItem
from app.helpers.timezone_utils import CHILE_TZ
import logging

logger = logging.getLogger(__name__)


class GuardarropiaTicketService:
    """Servicio para gestionar tickets QR de guardarropía"""
    
    @staticmethod
    def create_ticket_for_item(
        item: GuardarropiaItem,
        user_id: str,
        user_name: str,
        jornada_id: Optional[int] = None
    ) -> Tuple[bool, Optional[GuardarropiaTicket], str]:
        """
        Crea un ticket QR para un item de guardarropía
        
        Args:
            item: GuardarropiaItem - Item recién creado
            user_id: ID del usuario que creó el item
            user_name: Nombre del usuario
            jornada_id: ID de la jornada (opcional)
            
        Returns:
            Tuple[bool, Optional[GuardarropiaTicket], str]: (éxito, ticket, mensaje)
        """
        try:
            # Verificar que no exista ya un ticket para este item
            existing_ticket = GuardarropiaTicket.query.filter_by(item_id=item.id).first()
            if existing_ticket:
                logger.warning(f"⚠️  Ya existe ticket para item {item.id}: {existing_ticket.display_code}")
                return True, existing_ticket, "Ticket ya existe"
            
            # Generar códigos
            display_code = item.ticket_code  # Usar el ticket_code del item
            qr_token = GuardarropiaTicket.generate_qr_token()
            hash_integridad = GuardarropiaTicket.generate_hash_integridad(item.id, qr_token)
            
            # Determinar estado inicial
            initial_status = 'open'
            if item.price and item.price > 0:
                initial_status = 'paid'  # Si ya tiene precio, está pagado
            
            # Crear ticket
            ticket = GuardarropiaTicket(
                display_code=display_code,
                qr_token=qr_token,
                item_id=item.id,
                jornada_id=jornada_id,
                shift_date=item.shift_date,
                status=initial_status,
                created_by_user_id=user_id,
                created_by_user_name=user_name,
                price=item.price,
                payment_type=item.payment_type,
                hash_integridad=hash_integridad
            )
            
            # Si está pagado, marcar fecha de pago
            if initial_status == 'paid':
                ticket.paid_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
                ticket.paid_by = user_name
            
            db.session.add(ticket)
            db.session.flush()  # Para obtener el ID del ticket
            
            # Registrar log de emisión
            try:
                from flask import request as flask_request
                ip_address = flask_request.remote_addr if flask_request else None
                user_agent = flask_request.headers.get('User-Agent') if flask_request else None
            except:
                ip_address = None
                user_agent = None
            
            ticket_log = GuardarropiaTicketLog(
                ticket_id=ticket.id,
                action='issued',
                actor_user_id=user_id,
                actor_name=user_name,
                notes=f'Item depositado: {item.description or "Sin descripción"}',
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(ticket_log)
            
            db.session.commit()
            
            logger.info(f"✅ Ticket QR creado: {display_code} (token: {qr_token[:8]}...) para item {item.id}")
            
            return True, ticket, "Ticket creado correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear ticket QR de guardarropía: {e}", exc_info=True)
            return False, None, f"Error al crear ticket: {str(e)}"
    
    @staticmethod
    def get_ticket_by_qr_token(qr_token: str) -> Optional[GuardarropiaTicket]:
        """
        Obtiene un ticket por su QR token
        
        Args:
            qr_token: Token QR del ticket
            
        Returns:
            GuardarropiaTicket o None
        """
        try:
            return GuardarropiaTicket.query.filter_by(qr_token=qr_token).first()
        except Exception as e:
            logger.error(f"Error al buscar ticket por QR token: {e}", exc_info=True)
            return None
    
    @staticmethod
    def scan_ticket(
        qr_token: str,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Escanea un ticket por QR token
        
        Args:
            qr_token: Token QR del ticket
            actor_user_id: ID del usuario que escanea
            actor_name: Nombre del usuario
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (éxito, datos del ticket, mensaje)
        """
        try:
            ticket = GuardarropiaTicketService.get_ticket_by_qr_token(qr_token)
            
            if not ticket:
                return False, None, "Ticket no encontrado"
            
            # Validar que el ticket no esté anulado
            if ticket.is_void():
                return False, None, "Ticket anulado"
            
            # Validar que el ticket no esté ya retirado
            if ticket.is_checked_out():
                return False, None, "Ticket ya retirado"
            
            # Registrar log de escaneo
            try:
                from flask import request as flask_request
                ip_address = flask_request.remote_addr if flask_request else None
                user_agent = flask_request.headers.get('User-Agent') if flask_request else None
            except:
                ip_address = None
                user_agent = None
            
            ticket_log = GuardarropiaTicketLog(
                ticket_id=ticket.id,
                action='check_in',  # Escaneo para retiro
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(ticket_log)
            db.session.commit()
            
            # Preparar datos del ticket
            ticket_data = {
                'ticket': ticket.to_dict(),
                'can_check_out': ticket.can_check_out()
            }
            
            logger.info(f"✅ Ticket escaneado: {ticket.display_code} por {actor_name}")
            
            return True, ticket_data, "Ticket escaneado correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al escanear ticket: {e}", exc_info=True)
            return False, None, f"Error al escanear ticket: {str(e)}"
    
    @staticmethod
    def check_out_item(
        ticket_id: int,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Retira un item de guardarropía (check-out)
        
        Args:
            ticket_id: ID del ticket
            actor_user_id: ID del usuario que retira
            actor_name: Nombre del usuario
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            ticket = GuardarropiaTicket.query.get(ticket_id)
            if not ticket:
                return False, "Ticket no encontrado"
            
            if not ticket.can_check_out():
                return False, f"Ticket no permite retiro (estado: {ticket.status})"
            
            # Verificar que el item no esté ya retirado
            if ticket.item and ticket.item.is_retrieved():
                return False, "El item ya fue retirado"
            
            # Actualizar ticket
            ticket.status = 'checked_out'
            ticket.checked_out_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
            ticket.checked_out_by = actor_name
            
            # Actualizar item
            if ticket.item:
                ticket.item.status = 'retrieved'
                ticket.item.retrieved_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
                ticket.item.retrieved_by = actor_name
            
            # Registrar log
            try:
                from flask import request as flask_request
                ip_address = flask_request.remote_addr if flask_request else None
                user_agent = flask_request.headers.get('User-Agent') if flask_request else None
            except:
                ip_address = None
                user_agent = None
            
            ticket_log = GuardarropiaTicketLog(
                ticket_id=ticket_id,
                action='check_out',
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                notes=f'Item retirado: {ticket.item.description if ticket.item else "N/A"}',
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(ticket_log)
            db.session.commit()
            
            logger.info(f"✅ Item retirado: {ticket.display_code} por {actor_name}")
            
            return True, f"Item retirado correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al retirar item: {e}", exc_info=True)
            return False, f"Error al retirar item: {str(e)}"



