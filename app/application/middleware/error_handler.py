"""
Decorador para manejo automático de errores en rutas
Simplifica el manejo de errores en las funciones de ruta
"""
from functools import wraps
from flask import request, jsonify, flash, redirect, url_for
from typing import Callable, Optional, Tuple, Any
from app.application.exceptions.app_exceptions import APIError, InternalServerError
from app.domain.exceptions import DomainError
from app.application.validators.sale_id_validator import SaleIdValidationError
from app.application.validators.input_validator import InputValidationError
from app.application.validators.quantity_validator import QuantityValidationError


def handle_errors(
    redirect_on_error: Optional[str] = None,
    flash_message: Optional[str] = None,
    log_error: bool = True
):
    """
    Decorador para manejar errores automáticamente en rutas.
    
    Args:
        redirect_on_error: URL a la que redirigir en caso de error (None = usar referrer)
        flash_message: Mensaje flash personalizado (None = usar mensaje del error)
        log_error: Si debe loguear el error
    
    Ejemplo:
        @bp.route('/api/endpoint')
        @handle_errors()
        def my_endpoint():
            # Si ocurre un error, se maneja automáticamente
            raise NotFoundError("Recurso no encontrado")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            
            except APIError as e:
                # Errores de API ya estructurados
                if _is_json_request():
                    return jsonify(e.to_dict()), e.status_code
                else:
                    _handle_html_error(e, redirect_on_error, flash_message or e.user_message, log_error)
                    return redirect(_get_redirect_url(redirect_on_error)), 302
            
            except DomainError as e:
                # Errores de dominio - convertir a APIError
                api_error = _convert_domain_error(e)
                if _is_json_request():
                    return jsonify(api_error.to_dict()), api_error.status_code
                else:
                    _handle_html_error(api_error, redirect_on_error, flash_message or api_error.user_message, log_error)
                    return redirect(_get_redirect_url(redirect_on_error)), 302
            
            except (SaleIdValidationError, InputValidationError, QuantityValidationError) as e:
                # Errores de validación
                from app.application.exceptions.app_exceptions import ValidationError
                api_error = ValidationError(str(e), user_message=str(e))
                if _is_json_request():
                    return jsonify(api_error.to_dict()), api_error.status_code
                else:
                    _handle_html_error(api_error, redirect_on_error, flash_message or str(e), log_error)
                    return redirect(_get_redirect_url(redirect_on_error)), 302
            
            except Exception as e:
                # Errores no esperados
                api_error = InternalServerError(
                    message=f"Error inesperado: {type(e).__name__} - {str(e)}",
                    user_message="Ocurrió un error inesperado. Por favor, intenta nuevamente."
                )
                
                if log_error:
                    from flask import current_app
                    import traceback
                    current_app.logger.error(
                        f"Unhandled error in {func.__name__}: {str(e)}",
                        exc_info=True,
                        extra={'traceback': traceback.format_exc()}
                    )
                
                if _is_json_request():
                    return jsonify(api_error.to_dict()), api_error.status_code
                else:
                    _handle_html_error(api_error, redirect_on_error, flash_message or api_error.user_message, False)
                    return redirect(_get_redirect_url(redirect_on_error)), 302
        
        return wrapper
    return decorator


def _is_json_request() -> bool:
    """Verifica si la petición espera respuesta JSON"""
    return (
        request.is_json or
        request.path.startswith('/api/') or
        request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
    )


def _convert_domain_error(error: DomainError) -> APIError:
    """Convierte un error de dominio a un error de API"""
    from app.application.exceptions.app_exceptions import (
        BadRequestError, ForbiddenError, NotFoundError
    )
    
    error_class_name = error.__class__.__name__
    error_message = str(error)
    
    mapping = {
        'ShiftNotOpenError': lambda: ForbiddenError(
            message=error_message,
            user_message="No hay un turno abierto. Abre un turno antes de realizar esta operación."
        ),
        'ShiftAlreadyOpenError': lambda: BadRequestError(
            message=error_message,
            user_message="Ya hay un turno abierto."
        ),
        'FraudDetectedError': lambda: ForbiddenError(
            message=error_message,
            user_message="Fraude detectado. Se requiere autorización."
        ),
        'DeliveryValidationError': lambda: BadRequestError(
            message=error_message,
            user_message=error_message
        ),
    }
    
    converter = mapping.get(error_class_name)
    if converter:
        return converter()
    
    # Default: BadRequestError
    return BadRequestError(message=error_message, user_message=error_message)


def _handle_html_error(error: APIError, redirect_url: Optional[str], flash_msg: str, log: bool):
    """Maneja errores para respuestas HTML"""
    if log:
        from flask import current_app
        current_app.logger.error(
            f"Error [{error.error_code}]: {error.message}",
            extra={'error_code': error.error_code, 'status_code': error.status_code}
        )
    
    flash(flash_msg, "error")


def _get_redirect_url(redirect_url: Optional[str]) -> str:
    """Obtiene la URL de redirección apropiada"""
    if redirect_url:
        return redirect_url
    elif request.referrer:
        return request.referrer
    else:
        from flask import url_for
        return url_for('routes.scanner')














