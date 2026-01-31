"""
Helper para gestionar bloqueos de caja usando base de datos
Sistema robusto para evitar que múltiples usuarios usen la misma caja
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from flask import current_app
from app.models import db, RegisterLock
from app.helpers.timezone_utils import CHILE_TZ
import logging
import time

logger = logging.getLogger(__name__)

# Timeout automático de bloqueo (30 minutos de inactividad)
LOCK_TIMEOUT_MINUTES = 30


def get_employee_locks(employee_id: str) -> List[RegisterLock]:
    """
    Obtiene todas las cajas bloqueadas por un empleado específico
    
    Args:
        employee_id: ID del empleado
        
    Returns:
        List[RegisterLock]: Lista de bloqueos activos del empleado
    """
    try:
        employee_id = str(employee_id) if employee_id else ''
        # Usar hora de Chile (naive datetime) para consistencia
        now = datetime.now(CHILE_TZ).replace(tzinfo=None)
        
        # Obtener todos los bloqueos del empleado que no hayan expirado
        locks = RegisterLock.query.filter(
            RegisterLock.employee_id == employee_id
        ).all()
        
        # Filtrar bloqueos expirados
        active_locks = []
        for lock in locks:
            if lock.expires_at and lock.expires_at < now:
                # Bloqueo expirado, eliminarlo
                db.session.delete(lock)
            else:
                active_locks.append(lock)
        
        if active_locks:
            db.session.commit()
        
        return active_locks
    except Exception as e:
        logger.error(f"Error al obtener bloqueos del empleado: {e}")
        return []


def lock_register(register_id: str, employee_id: str, employee_name: str, session_id: Optional[str] = None, allow_multiple: bool = False) -> bool:
    """
    Bloquea una caja para un usuario específico con transacción atómica para evitar race conditions
    
    Args:
        register_id: ID de la caja
        employee_id: ID del empleado
        employee_name: Nombre del empleado
        session_id: ID de sesión (opcional)
        allow_multiple: Si es False, libera otras cajas del mismo empleado antes de bloquear esta
        
    Returns:
        bool: True si se bloqueó correctamente, False si ya está bloqueada por otro usuario
    """
    try:
        from sqlalchemy import select
        from sqlalchemy.exc import OperationalError
        
        # Normalizar employee_id a string para comparaciones consistentes
        employee_id = str(employee_id) if employee_id else ''
        
        # Usar transacción atómica para evitar race conditions
        # Primero: liberar otras cajas del mismo empleado si no se permiten múltiples
        if not allow_multiple:
            cleanup_duplicate_locks(employee_id)
            other_locks = get_employee_locks(employee_id)
            if other_locks:
                locks_freed = 0
                for lock in other_locks:
                    if str(lock.register_id) != str(register_id):
                        logger.info(f"🔓 Liberando caja {lock.register_id} del empleado {employee_name} para abrir caja {register_id}")
                        db.session.delete(lock)
                        locks_freed += 1
                
                if locks_freed > 0:
                    db.session.commit()
                    logger.info(f"✅ {locks_freed} caja(s) liberada(s) del empleado {employee_name}")
        
        # Verificar si la caja ya está bloqueada (con transacción)
        existing_lock = RegisterLock.query.get(register_id)
        
        if existing_lock:
            # Verificar si el bloqueo expiró
            # Usar hora de Chile (naive datetime) para comparaciones
            now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
            if existing_lock.expires_at and existing_lock.expires_at < now_chile:
                logger.info(f"🔓 Bloqueo de caja {register_id} expirado, liberándolo")
                db.session.delete(existing_lock)
                db.session.commit()
                existing_lock = None
            elif str(existing_lock.employee_id) != employee_id:
                # Caja bloqueada por otro usuario
                logger.warning(f"⚠️  Caja {register_id} ya está bloqueada por {existing_lock.employee_name} (ID: {existing_lock.employee_id})")
                return False
        
        # Crear o actualizar bloqueo usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        expires_at = now_chile + timedelta(minutes=LOCK_TIMEOUT_MINUTES)
        
        if existing_lock:
            # Actualizar bloqueo existente (mismo cajero)
            existing_lock.employee_id = employee_id
            existing_lock.employee_name = employee_name
            existing_lock.session_id = session_id
            existing_lock.locked_at = now_chile
            existing_lock.expires_at = expires_at
            logger.info(f"🔄 Bloqueo de caja {register_id} actualizado para {employee_name}")
        else:
            # Crear nuevo bloqueo
            lock = RegisterLock(
                register_id=register_id,
                employee_id=employee_id,
                employee_name=employee_name,
                session_id=session_id,
                locked_at=now_chile,
                expires_at=expires_at
            )
            db.session.add(lock)
            logger.info(f"✅ Nuevo bloqueo de caja {register_id} creado para {employee_name}")
        
        db.session.commit()
        
        # Registro de auditoría
        from app.helpers.sale_audit_logger import SaleAuditLogger
        SaleAuditLogger.log_register_lock(
            register_id=register_id,
            employee_id=employee_id,
            employee_name=employee_name,
            action='locked'
        )
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al bloquear caja: {e}", exc_info=True)
        return False


def unlock_register(register_id: str) -> bool:
    """
    Libera el bloqueo de una caja
    
    Args:
        register_id: ID de la caja
        
    Returns:
        bool: True si se liberó correctamente
    """
    try:
        lock = RegisterLock.query.get(register_id)
        if lock:
            db.session.delete(lock)
            db.session.commit()
            logger.info(f"✅ Caja {register_id} liberada")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al liberar caja: {e}")
        return False


def is_register_locked(register_id: str) -> bool:
    """
    Verifica si una caja está bloqueada
    
    Args:
        register_id: ID de la caja
        
    Returns:
        bool: True si está bloqueada y no expirada
    """
    try:
        lock = RegisterLock.query.get(register_id)
        if not lock:
            return False
        
        # Verificar si expiró usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        if lock.expires_at and lock.expires_at < now_chile:
            # Bloqueo expirado, eliminarlo
            db.session.delete(lock)
            db.session.commit()
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error al verificar bloqueo de caja: {e}")
        return False


def get_register_lock(register_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene información del bloqueo de una caja
    
    Args:
        register_id: ID de la caja
        
    Returns:
        Dict con información del bloqueo o None si no está bloqueada
    """
    try:
        lock = RegisterLock.query.get(register_id)
        if not lock:
            return None
        
        # Verificar si expiró usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        if lock.expires_at and lock.expires_at < now_chile:
            logger.info(f"🔓 Bloqueo de caja {register_id} expirado, eliminándolo")
            db.session.delete(lock)
            db.session.commit()
            return None
        
        lock_dict = lock.to_dict()
        # Asegurar que employee_id sea string para comparaciones consistentes
        if 'employee_id' in lock_dict:
            lock_dict['employee_id'] = str(lock_dict['employee_id'])
        return lock_dict
    except Exception as e:
        logger.error(f"Error al obtener bloqueo de caja: {e}")
        return None


def get_all_register_locks() -> List[Dict[str, Any]]:
    """Obtiene todos los bloqueos activos"""
    try:
        # Limpiar bloqueos expirados usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        expired_locks = RegisterLock.query.filter(
            RegisterLock.expires_at < now_chile
        ).all()
        for lock in expired_locks:
            db.session.delete(lock)
        db.session.commit()
        
        # Obtener bloqueos activos
        locks = RegisterLock.query.all()
        result = []
        for lock in locks:
            lock_dict = lock.to_dict()
            # Asegurar que employee_id sea string para comparaciones consistentes
            if 'employee_id' in lock_dict:
                lock_dict['employee_id'] = str(lock_dict['employee_id'])
            result.append(lock_dict)
        return result
    except Exception as e:
        logger.error(f"Error al obtener bloqueos: {e}")
        return []


def refresh_lock(register_id: str) -> bool:
    """
    Refresca el tiempo de expiración de un bloqueo (extiende el timeout)
    
    Args:
        register_id: ID de la caja
        
    Returns:
        bool: True si se refrescó correctamente
    """
    try:
        lock = RegisterLock.query.get(register_id)
        if not lock:
            return False
        
        # Extender expiración usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        lock.expires_at = now_chile + timedelta(minutes=LOCK_TIMEOUT_MINUTES)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al refrescar bloqueo: {e}")
        return False


def force_unlock_register(register_id: str, unlocked_by: str) -> bool:
    """
    Fuerza la liberación de una caja (solo para admins)
    
    Args:
        register_id: ID de la caja
        unlocked_by: Usuario que fuerza la liberación
        
    Returns:
        bool: True si se liberó correctamente
    """
    try:
        lock = RegisterLock.query.get(register_id)
        if lock:
            logger.warning(f"⚠️  Caja {register_id} forzada a liberar por {unlocked_by} (estaba bloqueada por {lock.employee_name})")
            db.session.delete(lock)
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al forzar liberación de caja: {e}")
        return False


def force_lock_register(register_id: str, employee_id: str, employee_name: str, session_id: Optional[str] = None) -> bool:
    """
    Fuerza el bloqueo de una caja, incluso si está bloqueada por otro usuario
    (usado cuando se valida PIN para retomar)
    IMPORTANTE: También libera otras cajas del mismo empleado para evitar múltiples bloqueos
    
    Args:
        register_id: ID de la caja
        employee_id: ID del empleado
        employee_name: Nombre del empleado
        session_id: ID de sesión (opcional)
        
    Returns:
        bool: True si se bloqueó correctamente
    """
    try:
        # Normalizar employee_id a string
        employee_id = str(employee_id) if employee_id else ''
        
        # PRIMERO: Liberar TODAS las otras cajas del mismo empleado (evitar múltiples bloqueos)
        other_locks = get_employee_locks(employee_id)
        if other_locks:
            for lock in other_locks:
                if str(lock.register_id) != str(register_id):
                    logger.info(f"🔓 Liberando caja {lock.register_id} del empleado {employee_name} antes de forzar bloqueo de caja {register_id}")
                    db.session.delete(lock)
            db.session.commit()
            logger.info(f"✅ {len([l for l in other_locks if str(l.register_id) != str(register_id)])} caja(s) liberada(s) del empleado {employee_name}")
        
        # SEGUNDO: Obtener bloqueo existente de la caja que se está intentando bloquear
        existing_lock = RegisterLock.query.get(register_id)
        
        if existing_lock:
            # Si está bloqueado por otro usuario, eliminarlo primero
            if str(existing_lock.employee_id) != employee_id:
                logger.info(f"🔄 Forzando cambio de bloqueo de caja {register_id} de {existing_lock.employee_name} a {employee_name}")
                db.session.delete(existing_lock)
                db.session.commit()
                existing_lock = None
        
        # Crear o actualizar bloqueo usando hora de Chile (naive datetime)
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        expires_at = now_chile + timedelta(minutes=LOCK_TIMEOUT_MINUTES)
        
        if existing_lock:
            # Actualizar bloqueo existente (mismo cajero)
            existing_lock.employee_id = employee_id
            existing_lock.employee_name = employee_name
            existing_lock.session_id = session_id
            existing_lock.locked_at = now_chile
            existing_lock.expires_at = expires_at
            logger.info(f"🔄 Bloqueo de caja {register_id} actualizado para {employee_name}")
        else:
            # Crear nuevo bloqueo
            lock = RegisterLock(
                register_id=register_id,
                employee_id=employee_id,
                employee_name=employee_name,
                session_id=session_id,
                locked_at=now_chile,
                expires_at=expires_at
            )
            db.session.add(lock)
            logger.info(f"✅ Nuevo bloqueo de caja {register_id} creado para {employee_name}")
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al forzar bloqueo de caja: {e}", exc_info=True)
        return False


def cleanup_duplicate_locks(employee_id: str) -> int:
    """
    Limpia bloqueos duplicados de un empleado, dejando solo el más reciente
    
    Args:
        employee_id: ID del empleado
        
    Returns:
        int: Número de bloqueos eliminados
    """
    try:
        employee_id = str(employee_id) if employee_id else ''
        all_locks = get_employee_locks(employee_id)
        
        if len(all_locks) <= 1:
            return 0
        
        # Ordenar por fecha de bloqueo (más reciente primero)
        all_locks.sort(key=lambda x: x.locked_at if x.locked_at else datetime.min, reverse=True)
        
        # Mantener solo el más reciente, eliminar los demás
        locks_to_delete = all_locks[1:]
        count = len(locks_to_delete)
        
        for lock in locks_to_delete:
            logger.warning(f"🗑️ Eliminando bloqueo duplicado: Caja {lock.register_id} del empleado {lock.employee_name}")
            db.session.delete(lock)
        
        if count > 0:
            db.session.commit()
            logger.info(f"✅ {count} bloqueo(s) duplicado(s) eliminado(s) del empleado {employee_id}")
        
        return count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al limpiar bloqueos duplicados: {e}")
        return 0


def unlock_all_registers() -> int:
    """
    Libera todas las cajas bloqueadas
    
    Returns:
        int: Número de cajas liberadas
    """
    try:
        all_locks = RegisterLock.query.all()
        count = len(all_locks)
        
        for lock in all_locks:
            db.session.delete(lock)
        
        db.session.commit()
        logger.info(f"✅ {count} caja(s) liberada(s)")
        return count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al liberar todas las cajas: {e}", exc_info=True)
        return 0

