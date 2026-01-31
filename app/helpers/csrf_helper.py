"""
Helper para manejar CSRF tokens en formularios y APIs
"""
from flask import current_app, request
from functools import wraps


def csrf_exempt_if_api(f):
    """
    Decorator que exime de CSRF si es una petición API (JSON)
    Útil para APIs que usan autenticación propia
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si es una petición JSON, probablemente es una API
        if request.is_json or request.path.startswith('/api/'):
            # Eximir de CSRF
            try:
                from flask_wtf.csrf import exempt
                return exempt(f)(*args, **kwargs)
            except ImportError:
                pass
        return f(*args, **kwargs)
    return decorated_function


def get_csrf_token():
    """Obtiene el token CSRF actual"""
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except:
        return ''





