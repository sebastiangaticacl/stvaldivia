"""
Rutas para el sistema de impresión automática de tickets
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging

from app.infrastructure.services.ticket_printer_service import TicketPrinterService
from app.infrastructure.external.pos_api_client import PhpPosApiClient
from app.application.services.service_factory import get_delivery_service

logger = logging.getLogger(__name__)

bp = Blueprint('ticket_printer', __name__, url_prefix='/api/ticket-printer')


@bp.route('/print', methods=['POST'])
def print_ticket():
    """
    Endpoint para imprimir un ticket cuando se completa una venta
    
    Body JSON:
    {
        "sale_id": "123",
        "register_id": "5",
        "employee_id": "10"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        sale_id = data.get('sale_id')
        if not sale_id:
            return jsonify({'error': 'sale_id es requerido'}), 400
        
        # Obtener datos de la venta desde PHP POS
        pos_client = PhpPosApiClient()
        sale_data = pos_client.get_sale(sale_id)
        
        if not sale_data:
            return jsonify({'error': f'No se encontró la venta {sale_id}'}), 404
        
        # Obtener items de la venta
        numeric_id = ''.join(filter(str.isdigit, str(sale_id)))
        items, error, _ = pos_client.get_sale_items(numeric_id)
        
        if error:
            return jsonify({'error': error}), 500
        
        if not items:
            return jsonify({'error': 'La venta no tiene items'}), 400
        
        # Obtener información de caja y vendedor
        register_id = data.get('register_id') or sale_data.get('register_id')
        employee_id = data.get('employee_id') or sale_data.get('employee_id')
        
        register_name = "POS"
        employee_name = "Vendedor"
        
        if register_id:
            register_info = pos_client.get_entity_details("registers", register_id)
            if register_info:
                register_name = register_info.get('name', f"Caja {register_id}")
        
        if employee_id:
            employee_info = pos_client.get_entity_details("employees", employee_id)
            if employee_info:
                first_name = employee_info.get('first_name', '')
                last_name = employee_info.get('last_name', '')
                employee_name = f"{first_name} {last_name}".strip() or f"Empleado {employee_id}"
        
        # Obtener nombre de impresora de configuración
        printer_name = current_app.config.get('TICKET_PRINTER_NAME')
        
        # Crear servicio de impresión e imprimir
        printer_service = TicketPrinterService(printer_name=printer_name)
        success = printer_service.print_ticket(
            sale_id=numeric_id,
            sale_data=sale_data,
            items=items,
            register_name=register_name,
            employee_name=employee_name
        )
        
        if success:
            logger.info(f"Ticket {sale_id} impreso correctamente desde {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': f'Ticket {sale_id} impreso correctamente',
                'sale_id': sale_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo imprimir el ticket'
            }), 500
            
    except Exception as e:
        logger.error(f"Error al imprimir ticket: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/health', methods=['GET'])
def health_check():
    """Verifica el estado del servicio de impresión"""
    try:
        printer_name = current_app.config.get('TICKET_PRINTER_NAME')
        printer_service = TicketPrinterService(printer_name=printer_name)
        
        return jsonify({
            'status': 'ok',
            'printer_name': printer_service.printer_name,
            'system': printer_service.system
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
