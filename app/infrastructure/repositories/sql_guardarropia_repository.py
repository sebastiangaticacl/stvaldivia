"""
Repositorio SQL para guardarropía
Implementación usando SQLAlchemy
"""
from typing import List, Optional
from datetime import datetime, date
from flask import current_app
from app.models import db
from app.models.guardarropia_models import GuardarropiaItem


class SqlGuardarropiaRepository:
    """
    Repositorio SQL para guardarropía usando SQLAlchemy
    """
    
    def save(self, item: GuardarropiaItem) -> bool:
        """Guarda un item de guardarropía en la base de datos"""
        try:
            db.session.add(item)
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar item de guardarropía: {e}")
            db.session.rollback()
            return False
    
    def find_by_ticket_code(self, ticket_code: str) -> Optional[GuardarropiaItem]:
        """Busca un item por código de ticket"""
        try:
            return GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        except Exception as e:
            current_app.logger.error(f"Error al buscar item por ticket_code: {e}")
            return None
    
    def find_by_id(self, item_id: int) -> Optional[GuardarropiaItem]:
        """Busca un item por ID"""
        try:
            return GuardarropiaItem.query.get(item_id)
        except Exception as e:
            current_app.logger.error(f"Error al buscar item por ID: {e}")
            return None
    
    def find_all(self, status: Optional[str] = None) -> List[GuardarropiaItem]:
        """Obtiene todos los items, opcionalmente filtrados por estado"""
        try:
            query = GuardarropiaItem.query
            if status:
                query = query.filter_by(status=status)
            return query.order_by(GuardarropiaItem.deposited_at.desc()).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener items de guardarropía: {e}")
            return []
    
    def find_by_shift_date(self, shift_date: str) -> List[GuardarropiaItem]:
        """Obtiene items de un turno específico por fecha (YYYY-MM-DD)"""
        try:
            return GuardarropiaItem.query.filter_by(
                shift_date=shift_date
            ).order_by(GuardarropiaItem.deposited_at.desc()).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener items por fecha de turno: {e}")
            return []
    
    def find_deposited(self, shift_date: Optional[str] = None) -> List[GuardarropiaItem]:
        """Obtiene todos los items depositados (no retirados y no eliminados)"""
        try:
            from sqlalchemy import or_
            query = GuardarropiaItem.query.filter_by(status='deposited')
            if shift_date:
                query = query.filter_by(shift_date=shift_date)
            # Excluir items eliminados (soft delete: tienen [ELIMINADO] en notas)
            query = query.filter(
                or_(
                    GuardarropiaItem.notes.is_(None),
                    ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
                )
            )
            return query.order_by(GuardarropiaItem.deposited_at.desc()).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener items depositados: {e}")
            return []
    
    def find_by_date_range(
        self, 
        start_date: date, 
        end_date: date,
        status: Optional[str] = None
    ) -> List[GuardarropiaItem]:
        """Obtiene items en un rango de fechas"""
        try:
            query = GuardarropiaItem.query.filter(
                GuardarropiaItem.deposited_at >= datetime.combine(start_date, datetime.min.time()),
                GuardarropiaItem.deposited_at <= datetime.combine(end_date, datetime.max.time())
            )
            if status:
                query = query.filter_by(status=status)
            return query.order_by(GuardarropiaItem.deposited_at.desc()).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener items por rango: {e}")
            return []
    
    def count_by_status(self, status: str, shift_date: Optional[str] = None) -> int:
        """Cuenta items por estado"""
        try:
            query = GuardarropiaItem.query.filter_by(status=status)
            if shift_date:
                query = query.filter_by(shift_date=shift_date)
            return query.count()
        except Exception as e:
            current_app.logger.error(f"Error al contar items por estado: {e}")
            return 0
    
    def update(self, item: GuardarropiaItem) -> bool:
        """Actualiza un item de guardarropía"""
        try:
            item.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error al actualizar item de guardarropía: {e}")
            db.session.rollback()
            return False
    
    def delete(self, item: GuardarropiaItem) -> bool:
        """Elimina un item de guardarropía"""
        try:
            db.session.delete(item)
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error al eliminar item de guardarropía: {e}")
            db.session.rollback()
            return False




