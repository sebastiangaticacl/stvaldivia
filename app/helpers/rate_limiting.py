import time
from collections import defaultdict
from flask import request, session

# Almacenamiento en memoria de intentos fallidos
_failed_attempts = defaultdict(list)
_max_attempts = 5
_lockout_duration = 300  # 5 minutos en segundos


def record_failed_attempt(identifier, max_attempts=None, lockout_duration=None):
    """
    Registra un intento fallido de autenticación
    
    Args:
        identifier: Identificador único (IP, employee_id, etc.)
        max_attempts: Máximo de intentos permitidos
        lockout_duration: Duración del bloqueo en segundos
    """
    max_att = max_attempts or _max_attempts
    lockout = lockout_duration or _lockout_duration
    
    current_time = time.time()
    
    # Limpiar intentos antiguos (más antiguos que el lockout_duration)
    _failed_attempts[identifier] = [
        attempt_time for attempt_time in _failed_attempts[identifier]
        if current_time - attempt_time < lockout
    ]
    
    # Agregar nuevo intento
    _failed_attempts[identifier].append(current_time)


def clear_failed_attempts(identifier):
    """Limpia los intentos fallidos para un identificador"""
    if identifier in _failed_attempts:
        del _failed_attempts[identifier]


def is_locked_out(identifier, max_attempts=None, lockout_duration=None):
    """
    Verifica si un identificador está bloqueado
    
    Returns:
        tuple: (is_locked, remaining_time, attempts)
    """
    max_att = max_attempts or _max_attempts
    lockout = lockout_duration or _lockout_duration
    
    if identifier not in _failed_attempts:
        return False, 0, 0
    
    current_time = time.time()
    attempts = _failed_attempts[identifier]
    
    # Limpiar intentos antiguos
    recent_attempts = [
        attempt_time for attempt_time in attempts
        if current_time - attempt_time < lockout
    ]
    _failed_attempts[identifier] = recent_attempts
    
    if len(recent_attempts) >= max_att:
        # Calcular tiempo restante del bloqueo
        oldest_attempt = min(recent_attempts)
        unlock_time = oldest_attempt + lockout
        remaining = max(0, unlock_time - current_time)
        return True, remaining, len(recent_attempts)
    
    return False, 0, len(recent_attempts)


def get_client_identifier():
    """Obtiene un identificador único para el cliente"""
    # Usar IP + User-Agent para mejor identificación
    ip = request.remote_addr or 'unknown'
    user_agent = request.headers.get('User-Agent', 'unknown')[:50]
    return f"{ip}:{hash(user_agent)}"


# Rate limiting por endpoint (requests por minuto)
ENDPOINT_RATE_LIMITS = {
    '/admin/generar-pagos': 30,  # 30 requests/minuto
    '/admin/liquidacion-pagos': 30,
    '/admin/turnos': 60,
    '/scanner': 120,
    '/entregar': 60,
    '/api/services/status': 60,
    '/admin/api/check-connection': 10,  # Más restrictivo
    'default': 120  # Límite por defecto
}


def check_endpoint_rate_limit(endpoint, client_id=None):
    """
    Verifica si un endpoint ha excedido su límite de rate
    
    Args:
        endpoint: Ruta del endpoint
        client_id: ID del cliente (opcional)
    
    Returns:
        Tuple[bool, str]: (permitido, mensaje)
    """
    if client_id is None:
        client_id = get_client_identifier()
    
    # Obtener límite para el endpoint
    limit = ENDPOINT_RATE_LIMITS.get(endpoint, ENDPOINT_RATE_LIMITS['default'])
    
    # Contar requests en la última ventana (1 minuto)
    current_time = time.time()
    window_start = current_time - 60
    
    # Limpiar entradas antiguas
    key = f"endpoint_rate:{endpoint}:{client_id}"
    
    if key not in _failed_attempts:
        _failed_attempts[key] = []
    
    # Filtrar intentos dentro de la ventana
    _failed_attempts[key] = [
        t for t in _failed_attempts[key] 
        if t > window_start
    ]
    
    # Verificar si excede el límite
    if len(_failed_attempts[key]) >= limit:
        return False, f"Rate limit excedido para {endpoint}. Máximo {limit} requests por minuto."
    
    # Registrar el request
    _failed_attempts[key].append(current_time)
    
    return True, "OK"




