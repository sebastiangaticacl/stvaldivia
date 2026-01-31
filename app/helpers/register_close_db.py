"""
Helper para gestionar cierres de caja usando base de datos
Reemplaza el sistema de archivos JSON por base de datos robusta
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from flask import current_app
from app.models import db, RegisterClose
from app.helpers.timezone_utils import CHILE_TZ
import pytz
import logging

logger = logging.getLogger(__name__)

# Tolerancia para considerar caja cuadrada
BALANCE_TOLERANCE = 100.0


def save_register_close(close_data: Dict[str, Any], validate_integrity: bool = True) -> Optional[RegisterClose]:
    """
    Guarda un nuevo cierre de caja en la base de datos con validación de integridad
    
    Args:
        close_data: Diccionario con los datos del cierre
        validate_integrity: Si True, valida la integridad antes de guardar
        
    Returns:
        RegisterClose: Instancia del modelo guardado o None si falla
    """
    try:
        # Validar integridad antes de guardar si está habilitado
        if validate_integrity:
            from app.helpers.financial_audit import validate_register_close_integrity
            
            # Crear objeto temporal para validación
            temp_close = RegisterClose(**close_data)
            is_valid, error_message = validate_register_close_integrity(temp_close)
            
            if not is_valid:
                logger.error(f"❌ Validación de integridad falló: {error_message}")
                raise ValueError(f"Error de integridad en cierre de caja: {error_message}")
        
        # Usar transacción atómica
        with db.session.begin():
            # Convertir closed_at de string a datetime si es necesario
            # Guardar directamente en hora de Chile (naive datetime) para consistencia
            closed_at = close_data.get('closed_at')
            if isinstance(closed_at, str):
                try:
                    closed_at = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                    if closed_at.tzinfo:
                        closed_at = closed_at.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    # Usar hora de Chile (naive datetime) directamente
                    closed_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
            elif closed_at is None:
                # Usar hora de Chile (naive datetime) directamente
                closed_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
            elif isinstance(closed_at, datetime):
                # Si ya es datetime, asegurar que sea naive (sin timezone)
                if closed_at.tzinfo:
                    closed_at = closed_at.replace(tzinfo=None)
            
            # Crear instancia del modelo
            register_close = RegisterClose(
                register_id=close_data.get('register_id'),
                register_name=close_data.get('register_name', 'Caja'),
                employee_id=str(close_data.get('employee_id', '')),
                employee_name=close_data.get('employee_name', 'Cajero'),
                shift_date=close_data.get('shift_date'),
                opened_at=close_data.get('opened_at'),
                closed_at=closed_at,
                expected_cash=float(close_data.get('expected_cash', 0)),
                expected_debit=float(close_data.get('expected_debit', 0)),
                expected_credit=float(close_data.get('expected_credit', 0)),
                actual_cash=float(close_data.get('actual_cash', 0)),
                actual_debit=float(close_data.get('actual_debit', 0)),
                actual_credit=float(close_data.get('actual_credit', 0)),
                diff_cash=float(close_data.get('diff_cash', 0)),
                diff_debit=float(close_data.get('diff_debit', 0)),
                diff_credit=float(close_data.get('diff_credit', 0)),
                difference_total=float(close_data.get('difference_total', 0)) or float(close_data.get('difference', 0)),  # Compatibilidad con ambos nombres
                total_sales=int(close_data.get('total_sales', 0)),
                total_amount=float(close_data.get('total_amount', 0)),
                notes=close_data.get('notes', ''),
                status=close_data.get('status', 'pending'),
                idempotency_key_close=close_data.get('idempotency_key_close')  # P0-011
            )
            
            # IMPORTANTE: Si total_amount es 0 pero hay montos reales, calcular automáticamente
            if register_close.total_amount == 0:
                actual_cash = float(register_close.actual_cash or 0)
                actual_debit = float(register_close.actual_debit or 0)
                actual_credit = float(register_close.actual_credit or 0)
                total_recaudado = actual_cash + actual_debit + actual_credit
                
                if total_recaudado > 0:
                    logger.info(f"💰 total_amount era 0, calculando desde montos reales: {total_recaudado}")
                    register_close.total_amount = total_recaudado
            
            # IMPORTANTE: Si difference_total es 0 pero hay diferencias individuales, recalcular
            # Esto corrige el problema cuando el resultado es positivo (sobrante)
            if register_close.difference_total == 0:
                diff_cash = float(register_close.diff_cash or 0)
                diff_debit = float(register_close.diff_debit or 0)
                diff_credit = float(register_close.diff_credit or 0)
                recalculated = diff_cash + diff_debit + diff_credit
                
                if recalculated != 0:
                    logger.info(f"⚠️ difference_total era 0, recalculando desde diferencias individuales: cash={diff_cash}, debit={diff_debit}, credit={diff_credit}, total={recalculated}")
                    register_close.difference_total = recalculated
            
            # Guardar en base de datos (dentro de la transacción)
            db.session.add(register_close)
            # Commit se hace automáticamente al salir del with
            
            logger.info(f"✅ Cierre de caja guardado en BD: {register_close.register_name} - {register_close.employee_name} (ID: {register_close.id}) - difference_total={register_close.difference_total}")
            return register_close
        # El commit se hace automáticamente al salir del with db.session.begin()

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al guardar cierre de caja en BD: {e}", exc_info=True)
        return None


def update_register_close(close_id: int, updates: Dict[str, Any]) -> bool:
    """
    Actualiza un cierre de caja existente
    
    Args:
        close_id: ID del cierre a actualizar
        updates: Diccionario con los campos a actualizar
        
    Returns:
        bool: True si se actualizó correctamente
    """
    try:
        register_close = RegisterClose.query.get(close_id)
        if not register_close:
            logger.warning(f"Cierre de caja no encontrado: ID {close_id}")
            return False
        
        # Actualizar campos
        for key, value in updates.items():
            if hasattr(register_close, key):
                if key in ['resolved_at'] and isinstance(value, str):
                    # Convertir string a datetime
                    try:
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        if value.tzinfo:
                            value = value.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        pass
                setattr(register_close, key, value)
        
        db.session.commit()
        logger.info(f"✅ Cierre de caja actualizado: ID {close_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar cierre de caja: {e}", exc_info=True)
        return False


def get_pending_closes() -> List[Dict[str, Any]]:
    """Obtiene solo los cierres pendientes de revisión"""
    try:
        # Query optimizada usando índice
        closes = RegisterClose.query.filter_by(status='pending').order_by(RegisterClose.closed_at.desc()).all()
        return [close.to_dict() for close in closes]
    except Exception as e:
        logger.error(f"Error al obtener cierres pendientes: {e}")
        return []


def get_balanced_closes() -> List[Dict[str, Any]]:
    """Obtiene los cierres cuadrados"""
    try:
        closes = RegisterClose.query.filter_by(status='balanced').order_by(RegisterClose.closed_at.desc()).all()
        return [close.to_dict() for close in closes]
    except Exception as e:
        logger.error(f"Error al obtener cierres cuadrados: {e}")
        return []


def get_resolved_closes(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtiene los cierres resueltos por el superadmin"""
    try:
        closes = RegisterClose.query.filter_by(status='resolved').order_by(RegisterClose.closed_at.desc()).limit(limit).all()
        return [close.to_dict() for close in closes]
    except Exception as e:
        logger.error(f"Error al obtener cierres resueltos: {e}")
        return []


def get_register_close_by_id(close_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un cierre específico por ID"""
    try:
        close = RegisterClose.query.get(close_id)
        return close.to_dict() if close else None
    except Exception as e:
        logger.error(f"Error al obtener cierre por ID: {e}")
        return None


def get_closes_by_register(register_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene los últimos cierres de una caja específica"""
    try:
        closes = RegisterClose.query.filter_by(register_id=register_id).order_by(RegisterClose.closed_at.desc()).limit(limit).all()
        return [close.to_dict() for close in closes]
    except Exception as e:
        logger.error(f"Error al obtener cierres por caja: {e}")
        return []


def accept_register_close(close_id: int, accepted_by: str, notes: str = '') -> bool:
    """
    Acepta un cierre de caja pendiente (cambia status a 'balanced')
    Esto desbloquea la caja para que pueda ser usada nuevamente
    
    Args:
        close_id: ID del cierre
        accepted_by: Usuario que acepta
        notes: Notas adicionales
        
    Returns:
        bool: True si se aceptó correctamente
    """
    try:
        register_close = RegisterClose.query.get(close_id)
        if not register_close:
            logger.warning(f"Cierre de caja no encontrado: ID {close_id}")
            return False
        
        if register_close.status != 'pending':
            logger.warning(f"Cierre {close_id} no está pendiente (status: {register_close.status})")
            return False
        
        # Cambiar status a 'balanced' (aceptado)
        register_close.status = 'balanced'
        register_close.resolved_by = accepted_by
        register_close.resolved_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
        if notes:
            register_close.resolution_notes = notes
        
        db.session.commit()
        
        # Desbloquear la caja ahora que el admin aceptó el cierre
        from app.helpers.register_lock_db import unlock_register
        try:
            unlock_register(register_close.register_id)
            logger.info(f"✅ Caja {register_close.register_id} desbloqueada después de aceptar cierre {close_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo desbloquear la caja {register_close.register_id}: {e}")
        
        logger.info(f"✅ Cierre de caja {close_id} aceptado por {accepted_by}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al aceptar cierre de caja: {e}", exc_info=True)
        return False


def resolve_register_close(close_id: int, resolved_by: str, resolution_notes: str = '') -> bool:
    """
    Resuelve un cierre de caja pendiente (marca como 'resolved')
    
    Args:
        close_id: ID del cierre
        resolved_by: Usuario que resuelve
        resolution_notes: Notas de resolución
        
    Returns:
        bool: True si se resolvió correctamente
    """
    return update_register_close(close_id, {
        'status': 'resolved',
        'resolved_by': resolved_by,
        'resolved_at': datetime.now(CHILE_TZ).replace(tzinfo=None),
        'resolution_notes': resolution_notes
    })

