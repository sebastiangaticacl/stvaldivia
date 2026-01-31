"""
Repositorio de Turnos SQL
Implementación de ShiftRepository usando SQLAlchemy.
"""
from typing import Optional, List
from datetime import datetime
from flask import current_app
import json

from app.models import db
from app.models.shift_models import Shift
from app.domain.shift import ShiftStatus, Shift as DomainShift
from app.infrastructure.repositories.shift_repository import ShiftRepository


class SqlShiftRepository(ShiftRepository):
    """
    Implementación SQL del repositorio de turnos.
    Usa el modelo Shift.
    """
    
    def __init__(self):
        """Inicializa el repositorio"""
        pass
    
    def _ensure_table_exists(self):
        """Verifica que la tabla existe"""
        try:
            from flask import has_app_context
            if not has_app_context():
                return
            
            # Intentar una consulta simple para verificar que la tabla existe
            try:
                Shift.query.limit(1).all()
            except Exception as e:
                # Si la tabla no existe, intentar crearla
                current_app.logger.warning(f"⚠️ Tabla shifts no encontrada, intentando crear: {e}")
                try:
                    db.create_all()
                    current_app.logger.info("✅ Tabla shifts creada exitosamente")
                except Exception as create_error:
                    current_app.logger.error(f"❌ Error al crear tabla shifts: {create_error}")
                    raise RuntimeError(
                        f"No se pudo crear la tabla shifts. "
                        f"Verifica la conexión a la base de datos: {create_error}"
                    ) from create_error
        except RuntimeError:
            raise
        except Exception as e:
            try:
                current_app.logger.warning(f"⚠️ Advertencia al verificar tabla shifts: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ Advertencia al verificar tabla shifts: {e}")
    
    def get_current_shift_status(self) -> ShiftStatus:
        """Obtiene el estado actual del turno"""
        try:
            self._ensure_table_exists()
            
            # Buscar el turno abierto más reciente
            current_shift = Shift.query.filter_by(is_open=True).order_by(Shift.created_at.desc()).first()
            
            if not current_shift:
                return ShiftStatus(is_open=False)
            
            # Convertir a ShiftStatus
            return ShiftStatus(
                is_open=current_shift.is_open,
                shift_date=current_shift.shift_date,
                opened_at=current_shift.opened_at,
                closed_at=current_shift.closed_at,
                opened_by=current_shift.opened_by,
                closed_by=current_shift.closed_by,
                fiesta_nombre=current_shift.fiesta_nombre,
                djs=current_shift.djs,
                barras_disponibles=json.loads(current_shift.barras_disponibles) if current_shift.barras_disponibles else [],
                bartenders=json.loads(current_shift.bartenders) if current_shift.bartenders else []
            )
        except Exception as e:
            error_msg = f"Error al obtener estado del turno SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return ShiftStatus(is_open=False)
    
    def save_shift_status(self, status: ShiftStatus) -> bool:
        """Guarda el estado del turno"""
        try:
            self._ensure_table_exists()
            
            if not status.shift_date:
                current_app.logger.error("No se puede guardar estado sin shift_date")
                return False
            
            # Buscar turno existente
            shift = Shift.query.filter_by(shift_date=status.shift_date).first()
            
            if shift:
                # Actualizar existente
                shift.is_open = status.is_open
                shift.opened_at = status.opened_at
                shift.closed_at = status.closed_at
                shift.opened_by = status.opened_by
                shift.closed_by = status.closed_by
                shift.fiesta_nombre = status.fiesta_nombre
                shift.djs = status.djs
                shift.barras_disponibles = json.dumps(status.barras_disponibles) if status.barras_disponibles else None
                shift.bartenders = json.dumps(status.bartenders) if status.bartenders else None
                shift.updated_at = datetime.utcnow()
            else:
                # Crear nuevo
                shift = Shift(
                    shift_date=status.shift_date,
                    is_open=status.is_open,
                    opened_at=status.opened_at,
                    closed_at=status.closed_at,
                    opened_by=status.opened_by,
                    closed_by=status.closed_by,
                    fiesta_nombre=status.fiesta_nombre,
                    djs=status.djs,
                    barras_disponibles=json.dumps(status.barras_disponibles) if status.barras_disponibles else None,
                    bartenders=json.dumps(status.bartenders) if status.bartenders else None
                )
                db.session.add(shift)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al guardar estado del turno SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
    
    def save_to_history(self, shift: DomainShift) -> bool:
        """Guarda un turno cerrado en el historial"""
        try:
            self._ensure_table_exists()
            
            # Buscar turno existente
            db_shift = Shift.query.filter_by(shift_date=shift.shift_date).first()
            
            if db_shift:
                # Actualizar con información de cierre
                db_shift.is_open = False
                db_shift.closed_at = shift.closed_at
                db_shift.closed_by = shift.closed_by
                db_shift.updated_at = datetime.utcnow()
            else:
                # Crear nuevo registro
                db_shift = Shift(
                    shift_date=shift.shift_date,
                    is_open=False,
                    opened_at=shift.opened_at,
                    closed_at=shift.closed_at,
                    opened_by=shift.opened_by,
                    closed_by=shift.closed_by,
                    fiesta_nombre=shift.fiesta_nombre,
                    djs=shift.djs,
                    barras_disponibles=json.dumps(shift.barras_disponibles) if shift.barras_disponibles else None,
                    bartenders=json.dumps(shift.bartenders) if shift.bartenders else None
                )
                db.session.add(db_shift)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al guardar historial de turno SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
    
    def get_shift_history(self, limit: int = 30) -> List[dict]:
        """Obtiene el historial de turnos cerrados"""
        try:
            self._ensure_table_exists()
            
            # Obtener turnos cerrados ordenados por fecha descendente
            shifts = Shift.query.filter_by(is_open=False).order_by(Shift.shift_date.desc()).limit(limit).all()
            
            history = []
            for shift in shifts:
                history.append(shift.to_dict())
            
            return history
        except Exception as e:
            error_msg = f"Error al obtener historial de turnos SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return []

