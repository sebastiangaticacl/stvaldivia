# Decorator para manejo mejorado de excepciones
# Archivo: app/helpers/exception_handler.py

from functools import wraps
from flask import jsonify, redirect, url_for, flash, request
from app.helpers.logger import get_logger

logger = get_logger(__name__)


def handle_exceptions(redirect_on_error=None, json_response=False, log_error=True):
    """
    Decorator para manejo centralizado de excepciones
    
    Args:
        redirect_on_error: URL para redirigir en caso de error (None = no redirigir)
        json_response: Si True, retorna JSON en lugar de HTML
        log_error: Si True, registra el error en logs
    
    Ejemplo:
        @bp.route('/endpoint')
        @handle_exceptions(redirect_on_error='routes.index', json_response=False)
        def my_endpoint():
            # código que puede lanzar excepciones
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                # Errores de validación
                error_msg = str(e) or 'Error de validación'
                if log_error:
                    logger.warning(f"Error de validación en {func.__name__}: {error_msg}")
                
                if json_response:
                    return jsonify({'error': error_msg, 'type': 'validation'}), 400
                
                flash(error_msg, 'error')
                if redirect_on_error:
                    return redirect(url_for(redirect_on_error))
                return jsonify({'error': error_msg}), 400
                
            except PermissionError as e:
                # Errores de permisos
                error_msg = str(e) or 'No tienes permisos para realizar esta acción'
                if log_error:
                    logger.warning(f"Error de permisos en {func.__name__}: {error_msg}")
                
                if json_response:
                    return jsonify({'error': error_msg, 'type': 'permission'}), 403
                
                flash(error_msg, 'error')
                if redirect_on_error:
                    return redirect(url_for(redirect_on_error))
                return jsonify({'error': error_msg}), 403
                
            except Exception as e:
                # Errores generales
                error_msg = 'Ha ocurrido un error inesperado'
                if log_error:
                    logger.error(
                        f"Error inesperado en {func.__name__}: {e}",
                        exc_info=True,
                        extra={
                            'endpoint': func.__name__,
                            'url': request.url if request else None,
                            'method': request.method if request else None
                        }
                    )
                
                if json_response:
                    return jsonify({
                        'error': error_msg,
                        'type': 'server_error',
                        'message': str(e) if logger.level == 10 else None  # Solo en debug
                    }), 500
                
                flash(error_msg, 'error')
                if redirect_on_error:
                    return redirect(url_for(redirect_on_error))
                return jsonify({'error': error_msg}), 500
        
        return wrapper
    return decorator


def require_auth(admin_only=False):
    """
    Decorator para requerir autenticación
    
    Args:
        admin_only: Si True, requiere ser administrador
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import session
            
            if admin_only:
                if not session.get('admin_logged_in'):
                    if request.is_json or request.path.startswith('/api'):
                        return jsonify({'error': 'No autorizado'}), 401
                    flash('Debes iniciar sesión como administrador', 'error')
                    return redirect(url_for('routes.login_admin'))
            else:
                if not session.get('bartender') and not session.get('admin_logged_in'):
                    if request.is_json or request.path.startswith('/api'):
                        return jsonify({'error': 'No autorizado'}), 401
                    flash('Debes iniciar sesión', 'error')
                    return redirect(url_for('routes.scanner'))
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_json_input(required_fields=None, validators=None):
    """
    Decorator para validar inputs JSON
    
    Args:
        required_fields: Lista de campos requeridos
        validators: Dict de {campo: función_validadora}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            try:
                data = request.get_json(silent=True) or {}
            except Exception:
                return jsonify({'error': 'Invalid JSON'}), 400
            
            # Validar campos requeridos
            if required_fields:
                missing = [f for f in required_fields if f not in data or data[f] is None]
                if missing:
                    return jsonify({
                        'error': f'Missing required fields: {", ".join(missing)}'
                    }), 400
            
            # Aplicar validadores
            if validators:
                for field, validator in validators.items():
                    if field in data and data[field] is not None:
                        try:
                            validated = validator(data[field])
                            if validated is None:
                                return jsonify({
                                    'error': f'Invalid value for field: {field}'
                                }), 400
                            data[field] = validated
                        except Exception as e:
                            return jsonify({
                                'error': f'Validation error for {field}: {str(e)}'
                            }), 400
            
            # Agregar datos validados a kwargs
            kwargs['validated_data'] = data
            return func(*args, **kwargs)
        return wrapper
    return decorator

