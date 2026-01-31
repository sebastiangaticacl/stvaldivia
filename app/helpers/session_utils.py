import time
from flask import session, request

SESSION_TIMEOUT = 1800  # 30 minutos en segundos


def update_session_activity():
    """Actualiza el tiempo de última actividad en la sesión"""
    session['last_activity'] = time.time()


def is_session_expired():
    """Verifica si la sesión ha expirado"""
    last_activity = session.get('last_activity')
    if not last_activity:
        return False
    
    elapsed = time.time() - last_activity
    return elapsed > SESSION_TIMEOUT


def check_session_timeout():
    """Verifica y limpia la sesión si ha expirado"""
    if is_session_expired():
        session.clear()
        return True
    return False


def get_session_time_remaining():
    """Obtiene el tiempo restante de la sesión en segundos"""
    last_activity = session.get('last_activity')
    if not last_activity:
        return SESSION_TIMEOUT
    
    elapsed = time.time() - last_activity
    remaining = SESSION_TIMEOUT - elapsed
    return max(0, remaining)




