"""
Sistema de rate limiting para APIs críticas
Previene abuso y sobrecarga del sistema
"""
import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Almacenamiento en memoria de rate limits
_rate_limit_store: Dict[str, Dict[str, Tuple[float, int]]] = defaultdict(dict)


def rate_limit(max_requests: int = 10, window_seconds: int = 60, key_func=None):
    """
    Decorador para rate limiting
    
    Args:
        max_requests: Número máximo de requests permitidos
        window_seconds: Ventana de tiempo en segundos
        key_func: Función para generar clave única (por defecto usa IP)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave única
            if key_func:
                key = key_func()
            else:
                # Por defecto usar IP + endpoint
                key = f"{request.remote_addr}:{request.endpoint}"
            
            current_time = time.time()
            window_key = f"{func.__name__}:{key}"
            
            # Limpiar entradas antiguas
            if window_key in _rate_limit_store:
                # Remover entradas fuera de la ventana
                _rate_limit_store[window_key] = {
                    k: v for k, v in _rate_limit_store[window_key].items()
                    if current_time - v[0] < window_seconds
                }
            else:
                _rate_limit_store[window_key] = {}
            
            # Contar requests en la ventana
            request_count = len(_rate_limit_store[window_key])
            
            if request_count >= max_requests:
                # Rate limit excedido
                logger.warning(
                    f"Rate limit excedido para {key} en {func.__name__}: "
                    f"{request_count}/{max_requests} en {window_seconds}s"
                )
                return jsonify({
                    'success': False,
                    'error': f'Rate limit excedido. Máximo {max_requests} requests por {window_seconds} segundos.',
                    'retry_after': window_seconds
                }), 429
            
            # Registrar request
            request_id = f"{current_time}:{request_count}"
            _rate_limit_store[window_key][request_id] = (current_time, request_count + 1)
            
            # Ejecutar función
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_rate_limit_status(key: str, func_name: str, window_seconds: int = 60) -> Dict:
    """
    Obtiene el estado del rate limit para una clave
    
    Args:
        key: Clave única
        func_name: Nombre de la función
        window_seconds: Ventana de tiempo
        
    Returns:
        Dict con información del rate limit
    """
    window_key = f"{func_name}:{key}"
    current_time = time.time()
    
    if window_key not in _rate_limit_store:
        return {
            'requests': 0,
            'limit': 0,
            'remaining': 0,
            'reset_at': current_time + window_seconds
        }
    
    # Limpiar entradas antiguas
    _rate_limit_store[window_key] = {
        k: v for k, v in _rate_limit_store[window_key].items()
        if current_time - v[0] < window_seconds
    }
    
    request_count = len(_rate_limit_store[window_key])
    
    return {
        'requests': request_count,
        'limit': 0,  # Se debe pasar como parámetro
        'remaining': 0,  # Se debe calcular
        'reset_at': current_time + window_seconds
    }


def clear_rate_limits():
    """Limpia todos los rate limits (útil para tests)"""
    global _rate_limit_store
    _rate_limit_store.clear()







