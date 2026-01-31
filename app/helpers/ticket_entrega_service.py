"""
Servicio para generar y gestionar Tickets de Entrega con QR
FASE 1: Generación automática de tickets QR al crear venta
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from flask import current_app
from app.models import db
from app.models.ticket_entrega_models import TicketEntrega, TicketEntregaItem, DeliveryLog
from app.models.pos_models import PosSale
from app.helpers.timezone_utils import CHILE_TZ
import logging

logger = logging.getLogger(__name__)


class TicketEntregaService:
    """Servicio para gestionar tickets de entrega con QR"""
    
    @staticmethod
    def create_ticket_for_sale(
        sale: PosSale,
        employee_id: str,
        employee_name: str,
        register_id: str
    ) -> Tuple[bool, Optional[TicketEntrega], str]:
        """
        Crea un ticket de entrega con QR para una venta
        
        Args:
            sale: PosSale - Venta recién creada
            employee_id: ID del empleado que creó la venta
            employee_name: Nombre del empleado
            register_id: ID de la caja
            
        Returns:
            Tuple[bool, Optional[TicketEntrega], str]: (éxito, ticket, mensaje)
        """
        try:
            # Validar que la venta no sea prueba/cortesía (a menos que esté permitido)
            allow_qr_for_test = current_app.config.get('ALLOW_QR_FOR_TEST', False)
            
            if sale.is_test or sale.is_courtesy:
                if not allow_qr_for_test:
                    logger.info(f"⏭️  Venta {sale.id} es prueba/cortesía, no se genera ticket QR")
                    return True, None, "Venta de prueba/cortesía, ticket QR omitido"
            
            # Verificar que no exista ya un ticket para esta venta
            existing_ticket = TicketEntrega.query.filter_by(sale_id=sale.id).first()
            if existing_ticket:
                logger.warning(f"⚠️  Ya existe ticket para venta {sale.id}: {existing_ticket.display_code}")
                return True, existing_ticket, "Ticket ya existe"
            
            # Validar que la venta tenga jornada_id
            if not sale.jornada_id:
                logger.error(f"❌ Venta {sale.id} no tiene jornada_id, no se puede crear ticket")
                return False, None, "Venta no tiene jornada asociada"
            
            # Generar códigos
            display_code = TicketEntrega.generate_display_code()
            qr_token = TicketEntrega.generate_qr_token()
            hash_integridad = TicketEntrega.generate_hash_integridad(sale.id, qr_token)
            
            # Crear ticket
            ticket = TicketEntrega(
                display_code=display_code,
                qr_token=qr_token,
                sale_id=sale.id,
                jornada_id=sale.jornada_id,
                shift_date=sale.shift_date,
                status='open',
                created_by_employee_id=employee_id,
                created_by_employee_name=employee_name,
                register_id=register_id,
                hash_integridad=hash_integridad
            )
            
            db.session.add(ticket)
            db.session.flush()  # Para obtener el ID del ticket
            
            # Crear items del ticket
            for sale_item in sale.items:
                ticket_item = TicketEntregaItem(
                    ticket_id=ticket.id,
                    product_id=str(sale_item.product_id),
                    product_name=sale_item.product_name,
                    qty=sale_item.quantity,
                    delivered_qty=0,
                    status='pending'
                )
                db.session.add(ticket_item)
            
            # Registrar log de creación
            delivery_log = DeliveryLog(
                ticket_id=ticket.id,
                action='created',
                bartender_user_id=employee_id,
                bartender_name=employee_name,
                ip_address=None,  # Se puede obtener de request si está disponible
                user_agent=None
            )
            db.session.add(delivery_log)
            
            db.session.commit()
            
            logger.info(f"✅ Ticket QR creado: {display_code} (token: {qr_token[:8]}...) para venta {sale.id}")
            
            return True, ticket, "Ticket creado correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear ticket QR: {e}", exc_info=True)
            return False, None, f"Error al crear ticket: {str(e)}"
    
    @staticmethod
    def get_ticket_by_qr_token(qr_token: str) -> Optional[TicketEntrega]:
        """
        Obtiene un ticket por su QR token
        
        Args:
            qr_token: Token QR del ticket
            
        Returns:
            TicketEntrega o None
        """
        try:
            return TicketEntrega.query.filter_by(qr_token=qr_token).first()
        except Exception as e:
            logger.error(f"Error al buscar ticket por QR token: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_ticket_by_display_code(display_code: str) -> Optional[TicketEntrega]:
        """
        Obtiene un ticket por su código visible
        
        Args:
            display_code: Código visible (ej: "BMB 11725")
            
        Returns:
            TicketEntrega o None
        """
        try:
            return TicketEntrega.query.filter_by(display_code=display_code).first()
        except Exception as e:
            logger.error(f"Error al buscar ticket por display_code: {e}", exc_info=True)
            return None
    
    @staticmethod
    def scan_ticket(
        qr_token: str,
        scanner_id: Optional[str] = None,
        scanner_name: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Escanea un ticket por QR token
        
        Args:
            qr_token: Token QR del ticket
            scanner_id: ID del escáner/bartender
            scanner_name: Nombre del bartender
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (éxito, datos del ticket, mensaje)
        """
        try:
            ticket = TicketEntregaService.get_ticket_by_qr_token(qr_token)
            
            if not ticket:
                return False, None, "Ticket no encontrado"
            
            # Validar que el ticket no esté anulado
            if ticket.is_void():
                return False, None, "Ticket anulado"
            
            # Validar que el ticket no esté completamente entregado
            if ticket.is_delivered():
                return False, None, "Ticket ya entregado completamente"
            
            # Validar que el ticket sea del turno actual (opcional, configurable)
            validate_shift = current_app.config.get('VALIDATE_TICKET_SHIFT', True)
            if validate_shift:
                from app.models.jornada_models import Jornada
                jornada_actual = Jornada.query.filter_by(
                    fecha_jornada=ticket.shift_date,
                    estado_apertura='abierto'
                ).first()
                
                if not jornada_actual:
                    # Permitir ver pero no entregar si es de otro turno
                    logger.warning(f"⚠️  Ticket {ticket.display_code} es de turno cerrado")
            
            # Registrar log de escaneo
            try:
                from flask import request as flask_request
                ip_address = flask_request.remote_addr if flask_request else None
                user_agent = flask_request.headers.get('User-Agent') if flask_request else None
            except:
                ip_address = None
                user_agent = None
            
            delivery_log = DeliveryLog(
                ticket_id=ticket.id,
                action='scan',
                bartender_user_id=scanner_id,
                bartender_name=scanner_name,
                scanner_device_id=scanner_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(delivery_log)
            db.session.commit()
            
            # Preparar datos del ticket
            ticket_data = {
                'ticket': ticket.to_dict(),
                'items': [item.to_dict() for item in ticket.items],
                'can_deliver': ticket.can_deliver()
            }
            
            logger.info(f"✅ Ticket escaneado: {ticket.display_code} por {scanner_name}")
            
            return True, ticket_data, "Ticket escaneado correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al escanear ticket: {e}", exc_info=True)
            return False, None, f"Error al escanear ticket: {str(e)}"
    
    @staticmethod
    def deliver_item(
        ticket_id: int,
        item_id: int,
        qty_to_deliver: int = 1,
        bartender_id: Optional[str] = None,
        bartender_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Entrega un item del ticket
        
        Args:
            ticket_id: ID del ticket
            item_id: ID del item
            qty_to_deliver: Cantidad a entregar (default 1)
            bartender_id: ID del bartender
            bartender_name: Nombre del bartender
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            ticket = TicketEntrega.query.get(ticket_id)
            if not ticket:
                return False, "Ticket no encontrado"
            
            if not ticket.can_deliver():
                return False, f"Ticket no permite entregas (estado: {ticket.status})"
            
            item = TicketEntregaItem.query.get(item_id)
            if not item or item.ticket_id != ticket_id:
                return False, "Item no encontrado o no pertenece al ticket"
            
            if not item.can_deliver(qty_to_deliver):
                return False, f"No se puede entregar {qty_to_deliver} unidades. Ya entregadas: {item.delivered_qty}, Total: {item.qty}"
            
            # Entregar item
            item.deliver(qty_to_deliver)
            
            # Actualizar estado del ticket
            ticket.update_status()
            
            # Registrar log
            delivery_log = DeliveryLog(
                ticket_id=ticket_id,
                item_id=item_id,
                action='deliver',
                bartender_user_id=bartender_id,
                bartender_name=bartender_name,
                qty=qty_to_deliver,
                product_name=item.product_name,
                ip_address=None,
                user_agent=None
            )
            db.session.add(delivery_log)
            db.session.commit()
            
            logger.info(f"✅ Item entregado: {item.product_name} x{qty_to_deliver} en ticket {ticket.display_code}")
            
            return True, f"Item entregado correctamente ({item.delivered_qty}/{item.qty})"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al entregar item: {e}", exc_info=True)
            return False, f"Error al entregar item: {str(e)}"

