"""
Servicio de Aplicación: Detección de Fraudes
Contiene la lógica de detección y autorización de fraudes.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from flask import current_app

from app.domain.exceptions import FraudDetectedError
from app.infrastructure.repositories.delivery_repository import DeliveryRepository


class FraudService:
    """
    Servicio de detección de fraudes.
    Encapsula la lógica de detección y validación de fraudes.
    """
    
    def __init__(
        self,
        delivery_repository: Optional[DeliveryRepository] = None,
        max_hours_old_ticket: int = 24,
        max_delivery_attempts: int = 3
    ):
        """
        Inicializa el servicio de fraudes.
        
        Args:
            delivery_repository: Repositorio de entregas (para contar intentos)
            max_hours_old_ticket: Horas máximas para considerar ticket antiguo
            max_delivery_attempts: Intentos máximos de entrega permitidos
        """
        self.delivery_repository = delivery_repository
        self.max_hours_old_ticket = max_hours_old_ticket
        self.max_delivery_attempts = max_delivery_attempts
    
    def check_ticket_age(self, sale_time_str: str, max_hours: Optional[int] = None) -> tuple[bool, float]:
        """
        Verifica si un ticket es antiguo.
        
        Args:
            sale_time_str: String de fecha en formato que devuelve la API
            max_hours: Horas máximas permitidas (None = usar config)
            
        Returns:
            tuple[bool, float]: (es_antiguo, días_de_antigüedad)
        """
        max_hours = max_hours or self.max_hours_old_ticket
        
        if not sale_time_str or sale_time_str == "Fecha no disponible":
            return False, 0.0
        
        try:
            # Intentar parsear diferentes formatos de fecha
            date_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y',
            ]
            
            sale_time = None
            for fmt in date_formats:
                try:
                    sale_time = datetime.strptime(sale_time_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if not sale_time:
                current_app.logger.warning(f"No se pudo parsear la fecha: {sale_time_str}")
                return False, 0.0
            
            now = datetime.now()
            time_diff = now - sale_time
            hours_diff = time_diff.total_seconds() / 3600
            days_diff = hours_diff / 24
            
            is_old = hours_diff > max_hours
            
            return is_old, days_diff
        except Exception as e:
            current_app.logger.error(f"Error al verificar antigüedad del ticket: {e}")
            return False, 0.0
    
    def count_delivery_attempts(self, sale_id: str) -> int:
        """
        Cuenta cuántas veces se ha intentado entregar un ticket.
        
        Args:
            sale_id: ID de la venta
            
        Returns:
            int: Número de intentos
        """
        if not self.delivery_repository:
            # Fallback: usar función existente si no hay repositorio
            try:
                from app.helpers.fraud_detection import count_delivery_attempts
                return count_delivery_attempts(sale_id)
            except:
                return 0
        
        # Usar repositorio para contar entregas
        deliveries = self.delivery_repository.find_by_sale_id(sale_id)
        return len(deliveries)
    
    def detect_fraud(
        self,
        sale_id: str,
        sale_time_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detecta fraudes en un ticket.
        
        Args:
            sale_id: ID de la venta
            sale_time_str: String de fecha de venta (opcional)
            
        Returns:
            dict con keys:
                - is_fraud: bool
                - fraud_type: str | None ('old_ticket', 'multiple_attempts', None)
                - message: str
                - details: dict
        """
        fraud_info = {
            'is_fraud': False,
            'fraud_type': None,
            'message': '',
            'details': {}
        }
        
        # Verificar múltiples intentos
        attempts = self.count_delivery_attempts(sale_id)
        if attempts >= self.max_delivery_attempts:
            fraud_info['is_fraud'] = True
            fraud_info['fraud_type'] = 'multiple_attempts'
            fraud_info['message'] = (
                f'FRAUDE DETECTADO: Este ticket ha sido intentado entregar {attempts} veces '
                f'(máximo permitido: {self.max_delivery_attempts})'
            )
            fraud_info['details'] = {
                'attempts': attempts,
                'max_attempts': self.max_delivery_attempts
            }
            return fraud_info
        
        # Verificar si el ticket es antiguo (si se proporciona sale_time_str)
        if sale_time_str:
            is_old, days_old = self.check_ticket_age(sale_time_str)
            if is_old:
                fraud_info['is_fraud'] = True
                fraud_info['fraud_type'] = 'old_ticket'
                fraud_info['message'] = (
                    f'FRAUDE DETECTADO: Este ticket es antiguo ({days_old:.1f} días). '
                    f'Requiere autorización del administrador.'
                )
                fraud_info['details'] = {
                    'days_old': round(days_old, 1),
                    'sale_time': sale_time_str
                }
                return fraud_info
        
        return fraud_info
    
    def check_fraud_before_delivery(
        self,
        sale_id: str,
        sale_time_str: Optional[str] = None
    ) -> None:
        """
        Verifica fraudes antes de permitir una entrega.
        Lanza excepción si se detecta fraude.
        
        Args:
            sale_id: ID de la venta
            sale_time_str: String de fecha de venta (opcional)
            
        Raises:
            FraudDetectedError: Si se detecta un fraude
        """
        fraud_info = self.detect_fraud(sale_id, sale_time_str)
        
        if fraud_info['is_fraud']:
            raise FraudDetectedError(
                fraud_info['message'],
                fraud_info['fraud_type'],
                fraud_info['details']
            )









