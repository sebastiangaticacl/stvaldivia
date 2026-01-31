"""
Repositorio SQL para entregas (Delivery)
Implementación usando SQLAlchemy
"""
from typing import List, Optional
from datetime import datetime, date
from flask import current_app
from app.models import db
from app.models.delivery_models import Delivery
from app.domain.delivery import Delivery as DeliveryDomain
from .delivery_repository import DeliveryRepository


class SqlDeliveryRepository(DeliveryRepository):
    """
    Implementación del repositorio usando SQLAlchemy
    """
    
    def save(self, delivery: DeliveryDomain) -> bool:
        """Guarda una entrega en la base de datos con transacción atómica"""
        try:
            from datetime import datetime
            from sqlalchemy import select
            
            # CORRECCIÓN: Usar transacción atómica para prevenir race conditions
            with db.session.begin():
                # Convertir timestamp string a DateTime
                try:
                    timestamp_dt = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    timestamp_dt = datetime.utcnow()
                
                # Convertir dominio a modelo
                delivery_model = Delivery(
                    sale_id=delivery.sale_id,
                    item_name=delivery.item_name,
                    qty=delivery.qty,
                    bartender=delivery.bartender,
                    barra=delivery.barra,
                    timestamp=timestamp_dt
                )
                
                db.session.add(delivery_model)
                # El commit se hace automáticamente al salir del bloque 'with'
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar entrega: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    def find_all(self) -> List[DeliveryDomain]:
        """Obtiene todas las entregas"""
        try:
            deliveries = Delivery.query.order_by(Delivery.timestamp.desc()).all()
            return [self._model_to_domain(d) for d in deliveries]
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas: {e}")
            return []
    
    def find_by_sale_id(self, sale_id: str, with_lock: bool = False) -> List[DeliveryDomain]:
        """Obtiene entregas de una venta específica
        
        Args:
            sale_id: ID de la venta
            with_lock: Si True, usa lock de fila para prevenir race conditions
        """
        try:
            if with_lock:
                # CORRECCIÓN: Usar lock para prevenir race conditions en validaciones
                from sqlalchemy import select
                deliveries = db.session.execute(
                    select(Delivery)
                    .where(Delivery.sale_id == sale_id)
                    .with_for_update()
                    .order_by(Delivery.timestamp.desc())
                ).scalars().all()
            else:
                deliveries = Delivery.query.filter_by(sale_id=sale_id).order_by(Delivery.timestamp.desc()).all()
            
            return [self._model_to_domain(d) for d in deliveries]
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas por sale_id: {e}")
            return []
    
    def find_by_shift_date(self, shift_date: str) -> List[DeliveryDomain]:
        """Obtiene entregas de un turno específico por fecha (YYYY-MM-DD)"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.timestamp.like(f"{shift_date}%")
            ).order_by(Delivery.timestamp.desc()).all()
            return [self._model_to_domain(d) for d in deliveries]
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas por fecha de turno: {e}")
            return []
    
    def find_by_date_range(self, start_date: date, end_date: date) -> List[DeliveryDomain]:
        """Obtiene entregas en un rango de fechas"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.timestamp >= datetime.combine(start_date, datetime.min.time()),
                Delivery.timestamp <= datetime.combine(end_date, datetime.max.time())
            ).order_by(Delivery.timestamp.desc()).all()
            return [self._model_to_domain(d) for d in deliveries]
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas por rango: {e}")
            return []
    
    def count_by_shift_date(self, shift_date: str) -> int:
        """Cuenta entregas de un turno específico por fecha (YYYY-MM-DD)"""
        try:
            count = Delivery.query.filter(
                Delivery.timestamp.like(f"{shift_date}%")
            ).count()
            return count
        except Exception as e:
            current_app.logger.error(f"Error al contar entregas por fecha: {e}")
            return 0
    
    def find_by_timestamp_after(self, timestamp: datetime) -> List[DeliveryDomain]:
        """Obtiene entregas posteriores a un timestamp"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.timestamp >= timestamp
            ).order_by(Delivery.timestamp.desc()).all()
            return [self._model_to_domain(d) for d in deliveries]
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas posteriores a timestamp: {e}")
            return []
    
    def _model_to_domain(self, model: Delivery) -> DeliveryDomain:
        """Convierte modelo SQL a dominio"""
        # Convertir DateTime a string ISO para compatibilidad con dominio
        timestamp_str = model.timestamp.strftime('%Y-%m-%d %H:%M:%S') if model.timestamp else ''
        
        return DeliveryDomain(
            sale_id=model.sale_id,
            item_name=model.item_name,
            qty=model.qty,
            bartender=model.bartender,
            barra=model.barra,
            timestamp=timestamp_str
        )
    
    def delete(self, delivery: DeliveryDomain) -> bool:
        """Elimina una entrega"""
        try:
            # Buscar entregas que coincidan
            deliveries = Delivery.query.filter_by(
                sale_id=delivery.sale_id,
                item_name=delivery.item_name,
                bartender=delivery.bartender,
                barra=delivery.barra
            ).all()
            
            # Si hay múltiples, eliminar la más reciente que coincida
            if deliveries:
                from datetime import datetime
                delivery_timestamp = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
                
                # Encontrar la más cercana al timestamp
                closest = min(deliveries, key=lambda d: abs((d.timestamp - delivery_timestamp).total_seconds()))
                db.session.delete(closest)
                db.session.commit()
                return True
            
            return False
        except Exception as e:
            current_app.logger.error(f"Error al eliminar entrega: {e}")
            db.session.rollback()
            return False

