"""
Decoradores para Rate Limiting
Simplifica la aplicación de rate limits en rutas
"""
from functools import wraps
from typing import Optional, Callable
from flask import request, jsonify
from app.infrastructure.rate_limiter.rate_limiter import RateLimiter, RateLimitExceeded
from app.infrastructure.rate_limiter.storage import MemoryRateLimitStorage
from app.application.exceptions.app_exceptions import RateLimitError


def rate_limit(
    max_requests: int = 100,
    per_seconds: int = 60,
    key_func: Optional[Callable] = None,
    error_message: Optional[str] = None
):
    """
    Decorador para aplicar rate limiting a una ruta.
    
    Args:
        max_requests: Máximo de solicitudes permitidas
        per_seconds: Ventana de tiempo en segundos
        key_func: Función para generar la clave única (None = usar IP)
        error_message: Mensaje de error personalizado
    
    Ejemplo:
        @bp.route('/api/endpoint')
        @rate_limit(max_requests=10, per_seconds=60)
        def my_endpoint():
            return jsonify({'status': 'ok'})
    """
    limiter = RateLimiter(
        max_requests=max_requests,
        window_seconds=per_seconds,
        storage=MemoryRateLimitStorage()
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave única
            if key_func:
                key = key_func()
            else:
                # Por defecto: usar IP + ruta
                ip = request.remote_addr or 'unknown'
                route = request.endpoint or request.path
                key = f"{ip}:{route}"
            
            try:
                # Verificar rate limit
                limiter.check(key)
                
                # Agregar headers con información del rate limit
                remaining = limiter.get_remaining(key)
                reset_time = limiter.get_reset_time(key)
                
                response = func(*args, **kwargs)
                
                # Agregar headers a la respuesta
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(max_requests)
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Reset'] = str(int(reset_time))
                elif isinstance(response, tuple):
                    # Si es tupla (response, status), modificar la respuesta
                    resp, status = response
                    if hasattr(resp, 'headers'):
                        resp.headers['X-RateLimit-Limit'] = str(max_requests)
                        resp.headers['X-RateLimit-Remaining'] = str(remaining)
                        resp.headers['X-RateLimit-Reset'] = str(int(reset_time))
                
                return response
                
            except RateLimitExceeded as e:
                # Si el método NO es GET/HEAD, siempre retornar JSON 429 (aunque no sea JSON request)
                if request.method not in ('GET', 'HEAD'):
                    return jsonify({
                        'error': error_message or 'Rate limit excedido',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': int(e.retry_after) if e.retry_after else None,
                        'path': request.path,
                        'method': request.method
                    }), 429
                
                # Para GET/HEAD, verificar si es JSON request o API path
                is_json_request = request.is_json
                is_api_path = request.path.startswith('/api/') or request.path.startswith('/admin/debug/')
                
                if is_json_request or is_api_path:
                    return jsonify({
                        'error': error_message or 'Rate limit excedido',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': int(e.retry_after) if e.retry_after else None
                    }), 429
                
                # Para GET/HEAD en páginas normales (no JSON, no API), usar redirect
                from flask import flash, redirect, url_for
                flash(
                    error_message or f"Demasiadas solicitudes. Intenta en {int(e.retry_after)} segundos.",
                    "error"
                )
                return redirect(request.referrer or url_for('routes.scanner')), 302
        
        return wrapper
    return decorator


def api_rate_limit(api_name: str = "default", error_message: Optional[str] = None):
    """
    Decorador para rate limiting de APIs externas.
    
    Args:
        api_name: Nombre de la API a proteger
        error_message: Mensaje de error personalizado
    
    Ejemplo:
        @api_rate_limit(api_name="php_pos")
        def call_pos_api():
            ...
    """
    from app.infrastructure.rate_limiter.rate_limiter import APIRateLimiter
    
    api_limiter = APIRateLimiter(storage=MemoryRateLimitStorage())
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                api_limiter.check(api_name)
                return func(*args, **kwargs)
            except RateLimitExceeded as e:
                from flask import current_app
                current_app.logger.warning(
                    f"Rate limit excedido para API {api_name}: {str(e)}"
                )
                raise RateLimitError(
                    retry_after=int(e.retry_after) if e.retry_after else None,
                    user_message=error_message or f"Límite de solicitudes a {api_name} excedido. Por favor, espera un momento."
                )
        
        return wrapper
    return decorator














