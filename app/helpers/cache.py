import time
from functools import wraps
from flask import current_app

# Cache simple en memoria (Tiempo de vida en segundos)
_cache = {}
_cache_config = {
    'employees': 1800,  # 30 minutos (reducir carga en API)
    'sale_items': 600,  # 10 minutos (reducir carga en API)
    'sale_details': 600,  # 10 minutos (reducir carga en API)
    'entity_details': 1800,  # 30 minutos (reducir carga en API)
    'all_sales': 300,  # 5 minutos (actualizado más frecuentemente para monitoreo)
    'entradas_sales': 1800,  # 30 minutos (reducir carga en API)
    'pos_products': 300,  # 5 minutos (productos del POS)
    'register_sales': 60,  # 1 minuto (monitoreo de ventas por caja)
}


def get_cache_key(prefix, *args, **kwargs):
    """Genera una clave única para el cache"""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return "|".join(key_parts)


def cached(cache_type, ttl=None):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        cache_type: Tipo de cache (employees, sale_items, etc.)
        ttl: Tiempo de vida en segundos (opcional, usa el config por defecto)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtener TTL del config o usar el proporcionado
            cache_ttl = ttl or _cache_config.get(cache_type, 60)
            
            # Generar clave única
            cache_key = get_cache_key(cache_type, *args, **kwargs)
            
            # Verificar si existe en cache y no ha expirado
            if cache_key in _cache:
                cached_value, cached_time = _cache[cache_key]
                if time.time() - cached_time < cache_ttl:
                    return cached_value
            
            # Ejecutar función y cachear resultado
            try:
                result = func(*args, **kwargs)
                _cache[cache_key] = (result, time.time())
                return result
            except Exception as e:
                # Si hay error, intentar devolver cache antiguo si existe
                if cache_key in _cache:
                    current_app.logger.warning(f"Error en {func.__name__}, usando cache antiguo: {e}")
                    return _cache[cache_key][0]
                raise
        
        return wrapper
    return decorator


def clear_cache(cache_type=None):
    """
    Limpia el cache
    
    Args:
        cache_type: Tipo específico a limpiar, o None para limpiar todo
    """
    if cache_type:
        keys_to_remove = [k for k in _cache.keys() if k.startswith(f"{cache_type}|")]
        for key in keys_to_remove:
            _cache.pop(key, None)
    else:
        _cache.clear()


def invalidate_sale_cache(sale_id):
    """Invalida el cache de una venta específica"""
    keys_to_remove = [
        k for k in _cache.keys() 
        if ('sale_items' in k or 'sale_details' in k) and str(sale_id) in k
    ]
    for key in keys_to_remove:
        _cache.pop(key, None)


def get_cache_stats():
    """Retorna estadísticas del cache"""
    total_keys = len(_cache)
    expired = 0
    valid = 0
    current_time = time.time()
    
    for key, (value, cached_time) in _cache.items():
        cache_type = key.split('|')[0]
        ttl = _cache_config.get(cache_type, 60)
        if current_time - cached_time < ttl:
            valid += 1
        else:
            expired += 1
    
    return {
        'total': total_keys,
        'valid': valid,
        'expired': expired
    }


def get_cached_value(key):
    """Obtiene un valor del cache por clave"""
    if key in _cache:
        value, cached_time = _cache[key]
        # Verificar si no ha expirado (usar TTL por defecto de 60s si no se especifica)
        cache_type = key.split('|')[0] if '|' in key else 'default'
        ttl = _cache_config.get(cache_type, 60)
        if time.time() - cached_time < ttl:
            return value
    return None


def set_cached_value(key, value, ttl=60):
    """Establece un valor en el cache"""
    _cache[key] = (value, time.time())




