"""
Gestor de sesiones mejorado con timeouts y limpieza automática
"""
import time
from datetime import datetime, timedelta
from flask import session, request
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Configuración de timeouts
SESSION_TIMEOUT_SECONDS = 1800  # 30 minutos
INACTIVITY_TIMEOUT_SECONDS = 900  # 15 minutos de inactividad


def update_session_activity():
    """Actualiza el timestamp de última actividad en la sesión"""
    session['last_activity'] = time.time()
    session.permanent = True


def is_session_valid() -> bool:
    """
    Verifica si la sesión es válida (no expirada)
    
    Returns:
        True si la sesión es válida, False si expiró
    """
    if not session.get('pos_logged_in'):
        return False
    
    last_activity = session.get('last_activity')
    if not last_activity:
        # Si no hay timestamp, asumir que es nueva
        update_session_activity()
        return True
    
    # Verificar timeout de inactividad
    inactive_time = time.time() - last_activity
    if inactive_time > INACTIVITY_TIMEOUT_SECONDS:
        logger.info(f"Sesión expirada por inactividad: {inactive_time:.0f}s")
        return False
    
    # Verificar timeout total de sesión
    session_start = session.get('session_start', last_activity)
    session_age = time.time() - session_start
    if session_age > SESSION_TIMEOUT_SECONDS:
        logger.info(f"Sesión expirada por tiempo total: {session_age:.0f}s")
        return False
    
    return True


def init_session():
    """Inicializa una nueva sesión con timestamps"""
    session['session_start'] = time.time()
    update_session_activity()


def clear_expired_session():
    """Limpia datos de sesión expirada"""
    session.pop('pos_logged_in', None)
    session.pop('pos_employee_id', None)
    session.pop('pos_employee_name', None)
    session.pop('pos_register_id', None)
    session.pop('pos_register_name', None)
    session.pop('pos_cart', None)
    session.pop('last_activity', None)
    session.pop('session_start', None)


def get_session_info() -> Dict[str, Any]:
    """
    Obtiene información de la sesión actual
    
    Returns:
        Dict con información de la sesión
    """
    last_activity = session.get('last_activity', 0)
    session_start = session.get('session_start', last_activity)
    
    return {
        'logged_in': session.get('pos_logged_in', False),
        'employee_id': session.get('pos_employee_id'),
        'employee_name': session.get('pos_employee_name'),
        'register_id': session.get('pos_register_id'),
        'register_name': session.get('pos_register_name'),
        'session_age': time.time() - session_start if session_start else 0,
        'inactive_time': time.time() - last_activity if last_activity else 0,
        'timeout_in': SESSION_TIMEOUT_SECONDS - (time.time() - session_start) if session_start else SESSION_TIMEOUT_SECONDS,
        'inactivity_timeout_in': INACTIVITY_TIMEOUT_SECONDS - (time.time() - last_activity) if last_activity else INACTIVITY_TIMEOUT_SECONDS
    }







