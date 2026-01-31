"""
Servicio de Aplicación: Gestión de Entregas (Deliveries)
Contiene la lógica de casos de uso para escanear ventas y registrar entregas.
"""
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from flask import current_app

from app.domain.delivery import Delivery
from app.domain.exceptions import ShiftNotOpenError, FraudDetectedError, DeliveryValidationError
from app.application.dto.delivery_dto import DeliveryRequest, ScanSaleRequest
from app.infrastructure.repositories.delivery_repository import DeliveryRepository, CsvDeliveryRepository
from app.infrastructure.repositories.shift_repository import ShiftRepository, JsonShiftRepository
from app.infrastructure.external.pos_api_client import PosApiClient, PhpPosApiClient
from app.application.services.fraud_service import FraudService
from app.application.services.shift_service import ShiftService


class DeliveryService:
    """
    Servicio de gestión de entregas.
    Encapsula la lógica de negocio de entregas.
    """
    
    def __init__(
        self,
        delivery_repository: Optional[DeliveryRepository] = None,
        shift_repository: Optional[ShiftRepository] = None,
        pos_client: Optional[PosApiClient] = None,
        fraud_service: Optional[FraudService] = None,
        shift_service: Optional[ShiftService] = None,
        event_publisher: Optional = None
    ):
        """
        Inicializa el servicio de entregas.
        
        Args:
            delivery_repository: Repositorio de entregas
            shift_repository: Repositorio de turnos (para validar turno abierto)
            pos_client: Cliente POS API
            fraud_service: Servicio de detección de fraudes
            shift_service: Servicio de turnos (para validar turno abierto)
            event_publisher: Publisher de eventos
        """
        self.delivery_repository = delivery_repository or CsvDeliveryRepository()
        self.shift_repository = shift_repository or JsonShiftRepository()
        self.pos_client = pos_client or PhpPosApiClient()
        self.fraud_service = fraud_service or FraudService(
            delivery_repository=self.delivery_repository
        )
        self.shift_service = shift_service or ShiftService(
            shift_repository=self.shift_repository
        )
        self.event_publisher = event_publisher
    
    def scan_sale(self, request: ScanSaleRequest) -> Dict[str, Any]:
        """
        Escanea una venta LOCAL y obtiene sus detalles.
        """
        # Validar request
        request.validate()
        
        # Normalizar sale_id
        numeric_id = request.get_numeric_id()
        if not numeric_id:
            raise ValueError("sale_id inválido o vacío")
        
        try:
            from app.models import PosSale, PosSaleItem
            
            # Buscar venta local
            sale = PosSale.query.get(int(numeric_id))
            
            if not sale:
                return {
                    'error': f'No se encontró la venta {numeric_id} en el sistema local.',
                    'items': []
                }
            
            # Formatear items
            items = []
            for item in sale.items:
                items.append({
                    'item_id': str(item.product_id),
                    'name': item.product_name,
                    'quantity': float(item.quantity),
                    'price': float(item.item_price),
                    'total': float(item.total_price),
                    'category': 'General' # Podríamos buscar la categoría del producto si es necesario
                })
            
            return {
                'venta_id': str(sale.id),
                'fecha_venta': sale.sale_time.strftime('%Y-%m-%d %H:%M:%S'),
                'items': items,
                'vendedor': sale.employee_name,
                'comprador': f"Cliente {sale.customer_id}" if sale.customer_id else "Cliente General",
                'caja': f"Caja {sale.register_id}",
                'sale_data': { # Datos crudos para compatibilidad
                    'sale_id': str(sale.id),
                    'sale_time': sale.sale_time.isoformat(),
                    'register_id': sale.register_id,
                    'employee_id': sale.employee_id
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al escanear venta local: {e}")
            return {
                'error': f'Error al procesar venta: {str(e)}',
                'items': []
            }
    
    def register_delivery(self, request: DeliveryRequest) -> Tuple[bool, str]:
        """
        Registra una entrega.
        
        Args:
            request: DTO con información de la entrega
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
            
        Raises:
            ShiftNotOpenError: Si no hay turno abierto
            FraudDetectedError: Si se detecta fraude
            DeliveryValidationError: Si los datos son inválidos
        """
        # Validar request
        try:
            request.validate()
        except ValueError as e:
            raise DeliveryValidationError(f"Datos de entrega inválidos: {str(e)}")
        
        # Verificar que hay turno abierto
        if not self.shift_service.is_shift_open():
            raise ShiftNotOpenError("No hay un turno abierto. Abre un turno antes de registrar entregas.")
        
        # Crear entidad Delivery
        delivery = Delivery(
            sale_id=request.sale_id,
            item_name=request.item_name,
            qty=request.qty,
            bartender=request.bartender,
            barra=request.barra,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            admin_user=request.admin_user  # Agregar admin_user si existe
        )
        
        # Validar entidad
        try:
            delivery.validate()
        except ValueError as e:
            raise DeliveryValidationError(f"Entidad Delivery inválida: {str(e)}")
        
        # Guardar en repositorio
        if not self.delivery_repository.save(delivery):
            return False, "Error al guardar la entrega"
        
        # Invalidar cache de la venta (usar función existente)
        try:
            from app.helpers.cache import invalidate_sale_cache
            invalidate_sale_cache(request.sale_id)
        except:
            pass
        
        # Registrar en inventario (si está disponible)
        try:
            from app.application.services.service_factory import get_inventory_service
            inventory_service = get_inventory_service()
            inventory_service.record_delivery(
                barra=request.barra,
                product_name=request.item_name,
                quantity=request.qty
            )
        except Exception as e:
            # No fallar si el inventario no está disponible
            current_app.logger.warning(f"No se pudo registrar entrega en inventario: {e}")
        
        # Emitir eventos
        if self.event_publisher:
            delivery_dict = delivery.to_dict()
            self.event_publisher.emit_delivery_created(delivery_dict)
        
        current_app.logger.info(
            f"Entrega registrada: {request.sale_id} - {request.item_name} x{request.qty} "
            f"({request.bartender} en {request.barra})"
        )
        
        return True, f"Entrega registrada: {request.item_name} x{request.qty}"
    
    def register_delivery_with_fraud_check(
        self,
        request: DeliveryRequest,
        sale_time_str: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Registra una entrega con verificación de fraudes.
        
        Args:
            request: DTO con información de la entrega
            sale_time_str: Fecha de venta para verificar antigüedad (opcional)
            
        Returns:
            Tuple[bool, str, Optional[dict]]: (éxito, mensaje, info_fraude)
            
            Si se detecta fraude, retorna:
            (False, mensaje, dict_con_info_fraude)
        """
        # Verificar fraudes antes de registrar
        fraud_info = self.fraud_service.detect_fraud(request.sale_id, sale_time_str)
        
        if fraud_info['is_fraud']:
            # Retornar información del fraude sin registrar
            return False, fraud_info['message'], fraud_info
        
        # Si no hay fraude, registrar normalmente
        success, message = self.register_delivery(request)
        return success, message, None
    
    def get_deliveries_by_shift_date(self, shift_date: str) -> List[Delivery]:
        """
        Obtiene entregas de un turno específico.
        
        Args:
            shift_date: Fecha del turno (YYYY-MM-DD)
            
        Returns:
            List[Delivery]: Lista de entregas
        """
        return self.delivery_repository.find_by_shift_date(shift_date)
    
    def get_delivery_history(self) -> List[Delivery]:
        """
        Obtiene todas las entregas.
        
        Returns:
            List[Delivery]: Lista de todas las entregas
        """
        return self.delivery_repository.find_all()

