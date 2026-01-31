"""
Repositorio de Entregas (Deliveries)
Interfaz e implementación usando Base de Datos.
"""
from abc import ABC, abstractmethod
import os
import csv
from typing import List, Optional
from flask import current_app
from datetime import datetime

from app.domain.delivery import Delivery
from app.models import db
from app.models.delivery_models import Delivery as DeliveryModel


class DeliveryRepository(ABC):
    """Interfaz del repositorio de entregas"""
    
    @abstractmethod
    def save(self, delivery: Delivery) -> bool:
        """Guarda una entrega"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Delivery]:
        """Obtiene todas las entregas"""
        pass
    
    @abstractmethod
    def find_by_shift_date(self, shift_date: str) -> List[Delivery]:
        """Obtiene entregas de un turno específico por fecha"""
        pass
    
    @abstractmethod
    def find_by_sale_id(self, sale_id: str) -> List[Delivery]:
        """Obtiene entregas de una venta específica"""
        pass
    
    @abstractmethod
    def delete(self, delivery: Delivery) -> bool:
        """Elimina una entrega"""
        pass
    
    @abstractmethod
    def count_by_shift_date(self, shift_date: str) -> int:
        """Cuenta entregas de un turno específico"""
        pass


class CsvDeliveryRepository(DeliveryRepository):
    """
    Implementación del repositorio usando Base de Datos.
    Migrado desde CSV a SQL.
    """
    
    def _domain_to_model(self, delivery: Delivery) -> DeliveryModel:
        """Convierte Delivery del dominio a DeliveryModel de BD"""
        try:
            timestamp = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()
        
        return DeliveryModel(
            sale_id=delivery.sale_id,
            item_name=delivery.item_name,
            qty=delivery.qty,
            bartender=delivery.bartender,
            barra=delivery.barra,
            admin_user=getattr(delivery, 'admin_user', None),  # Agregar admin_user si existe
            timestamp=timestamp
        )
    
    def _model_to_domain(self, model: DeliveryModel) -> Delivery:
        """Convierte DeliveryModel de BD a Delivery del dominio"""
        return Delivery(
            sale_id=model.sale_id,
            item_name=model.item_name,
            qty=model.qty,
            bartender=model.bartender,
            barra=model.barra,
            timestamp=model.timestamp.strftime('%Y-%m-%d %H:%M:%S') if model.timestamp else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            admin_user=getattr(model, 'admin_user', None)  # Agregar admin_user si existe
        )
    
    def save(self, delivery: Delivery) -> bool:
        """Guarda una entrega en la base de datos"""
        try:
            # Validar la entrega antes de guardar
            delivery.validate()
            
            # Convertir a modelo de BD y guardar
            delivery_model = self._domain_to_model(delivery)
            db.session.add(delivery_model)
            db.session.commit()
            
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al guardar entrega en BD: {e}")
            return False
    
    def find_all(self) -> List[Delivery]:
        """Obtiene todas las entregas desde la base de datos"""
        try:
            models = DeliveryModel.query.order_by(DeliveryModel.timestamp.desc()).all()
            return [self._model_to_domain(m) for m in models]
        except Exception as e:
            current_app.logger.error(f"Error al cargar entregas desde BD: {e}")
            return []
    
    def find_by_shift_date(self, shift_date: str) -> List[Delivery]:
        """Obtiene entregas de un turno específico por fecha (YYYY-MM-DD)"""
        try:
            # Buscar entregas donde la fecha del timestamp coincida
            start_date = datetime.strptime(shift_date, '%Y-%m-%d')
            end_date = datetime.combine(start_date.date(), datetime.max.time())
            
            models = DeliveryModel.query.filter(
                DeliveryModel.timestamp >= start_date,
                DeliveryModel.timestamp <= end_date
            ).order_by(DeliveryModel.timestamp.desc()).all()
            
            return [self._model_to_domain(m) for m in models]
        except Exception as e:
            current_app.logger.error(f"Error al buscar entregas por fecha desde BD: {e}")
            return []
    
    def find_by_sale_id(self, sale_id: str) -> List[Delivery]:
        """Obtiene entregas de una venta específica desde la base de datos"""
        try:
            models = DeliveryModel.query.filter_by(sale_id=str(sale_id)).order_by(DeliveryModel.timestamp.desc()).all()
            # También buscar sin prefijo BMB
            sale_id_clean = sale_id.replace('BMB ', '').replace('BMB', '').strip()
            if sale_id_clean != sale_id:
                models_clean = DeliveryModel.query.filter_by(sale_id=sale_id_clean).order_by(DeliveryModel.timestamp.desc()).all()
                models.extend(models_clean)
            
            return [self._model_to_domain(m) for m in models]
        except Exception as e:
            current_app.logger.error(f"Error al buscar entregas por sale_id desde BD: {e}")
            return []
    
    def delete(self, delivery: Delivery) -> bool:
        """Elimina una entrega de la base de datos"""
        try:
            # Buscar la entrega en BD
            try:
                timestamp = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                timestamp = None
            
            query = DeliveryModel.query.filter_by(
                sale_id=delivery.sale_id,
                item_name=delivery.item_name
            )
            
            if timestamp:
                query = query.filter_by(timestamp=timestamp)
            
            delivery_model = query.first()
            
            if delivery_model:
                db.session.delete(delivery_model)
                db.session.commit()
                return True
            
            return False
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al eliminar entrega de BD: {e}")
            return False
    
    def count_by_shift_date(self, shift_date: str) -> int:
        """Cuenta entregas de un turno específico desde la base de datos"""
        try:
            start_date = datetime.strptime(shift_date, '%Y-%m-%d')
            end_date = datetime.combine(start_date.date(), datetime.max.time())
            
            count = DeliveryModel.query.filter(
                DeliveryModel.timestamp >= start_date,
                DeliveryModel.timestamp <= end_date
            ).count()
            
            return count
        except Exception as e:
            current_app.logger.error(f"Error al contar entregas por fecha desde BD: {e}")
            return 0









