"""
Servicio de Monitoreo de Ventas
Monitorea ventas nuevas y dispara impresión automática de tickets
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Set, Optional
from flask import current_app
import logging
import requests

from app.infrastructure.services.ticket_printer_service import TicketPrinterService
from app.infrastructure.external.pos_api_client import PhpPosApiClient

logger = logging.getLogger(__name__)


class SaleMonitorService:
    """Servicio que monitorea ventas nuevas y las imprime automáticamente"""
    
    def __init__(self, polling_interval: int = 10, printer_name: Optional[str] = None):
        """
        Inicializa el servicio de monitoreo
        
        Args:
            polling_interval: Intervalo en segundos para verificar ventas nuevas
            printer_name: Nombre de la impresora
        """
        self.polling_interval = polling_interval
        self.printer_service = TicketPrinterService(printer_name=printer_name)
        self.pos_client = PhpPosApiClient()
        self.monitored_sales: Set[str] = set()  # IDs de ventas ya procesadas
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_check_time = datetime.now() - timedelta(minutes=5)
    
    def start_monitoring(self):
        """Inicia el monitoreo en un hilo separado"""
        if self.is_running:
            logger.warning("El monitoreo ya está en ejecución")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Servicio de monitoreo de ventas iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Servicio de monitoreo de ventas detenido")
    
    def _monitor_loop(self):
        """Loop principal de monitoreo"""
        while self.is_running:
            try:
                self._check_new_sales()
                time.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(self.polling_interval)
    
    def _check_new_sales(self):
        """Verifica ventas nuevas y las imprime"""
        try:
            # Obtener ventas recientes (últimos 5 minutos)
            end_time = datetime.now()
            start_time = self.last_check_time
            
            # Obtener ventas desde la API
            sales = self.pos_client.get_all_sales(
                limit=100,
                max_results=100,
                use_pagination=False,
                start_date=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                end_date=end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            )
            
            new_sales_count = 0
            for sale in sales:
                sale_id = str(sale.get('sale_id', ''))
                
                # Normalizar sale_id
                numeric_id = ''.join(filter(str.isdigit, sale_id))
                if not numeric_id:
                    continue
                
                # Verificar si ya fue procesada
                if numeric_id in self.monitored_sales:
                    continue
                
                # Marcar como procesada
                self.monitored_sales.add(numeric_id)
                
                # Imprimir ticket
                try:
                    self._print_sale_ticket(numeric_id, sale)
                    new_sales_count += 1
                except Exception as e:
                    logger.error(f"Error al imprimir ticket {numeric_id}: {e}")
            
            if new_sales_count > 0:
                logger.info(f"Se procesaron {new_sales_count} ventas nuevas")
            
            # Actualizar tiempo de última verificación
            self.last_check_time = end_time
            
            # Limpiar ventas antiguas del set (mantener solo últimas 1000)
            if len(self.monitored_sales) > 1000:
                # Mantener solo las más recientes
                self.monitored_sales = set(list(self.monitored_sales)[-1000:])
                
        except Exception as e:
            logger.error(f"Error al verificar ventas nuevas: {e}")
    
    def _print_sale_ticket(self, sale_id: str, sale_data: dict):
        """Imprime el ticket de una venta"""
        try:
            # Obtener items de la venta
            items, error, _ = self.pos_client.get_sale_items(sale_id)
            
            if error or not items:
                logger.warning(f"No se pudieron obtener items para venta {sale_id}")
                return
            
            # Obtener información de caja y vendedor
            register_id = sale_data.get('register_id')
            employee_id = sale_data.get('employee_id')
            
            register_name = "POS"
            employee_name = "Vendedor"
            
            if register_id:
                register_info = self.pos_client.get_entity_details("registers", register_id)
                if register_info:
                    register_name = register_info.get('name', f"Caja {register_id}")
            
            if employee_id:
                employee_info = self.pos_client.get_entity_details("employees", employee_id)
                if employee_info:
                    first_name = employee_info.get('first_name', '')
                    last_name = employee_info.get('last_name', '')
                    employee_name = f"{first_name} {last_name}".strip() or f"Empleado {employee_id}"
            
            # Imprimir
            success = self.printer_service.print_ticket(
                sale_id=sale_id,
                sale_data=sale_data,
                items=items,
                register_name=register_name,
                employee_name=employee_name
            )
            
            if success:
                logger.info(f"Ticket {sale_id} impreso automáticamente")
            else:
                logger.warning(f"No se pudo imprimir ticket {sale_id}")
                
        except Exception as e:
            logger.error(f"Error al imprimir ticket {sale_id}: {e}")







