"""
Handlers Centralizados de Errores
Manejo consistente de errores en toda la aplicación
"""
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from typing import Tuple, Optional
import traceback
from app.application.exceptions.app_exceptions import APIError
from app.domain.exceptions import DomainError
from app.application.validators.sale_id_validator import SaleIdValidationError
from app.application.validators.input_validator import InputValidationError
from app.application.validators.quantity_validator import QuantityValidationError


def is_json_request() -> bool:
    """Verifica si la petición espera una respuesta JSON"""
    return (
        request.is_json or
        request.path.startswith('/api/') or
        request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
    )


def handle_api_error(error: APIError) -> Tuple[str, int]:
    """
    Maneja un error de API y retorna respuesta JSON.
    
    Args:
        error: Error de API
        
    Returns:
        Tuple[str, int]: (respuesta JSON, código de estado)
    """
    from flask import current_app
    
    # Log del error (con detalles en desarrollo, sin detalles en producción)
    if current_app.config.get('DEBUG'):
        current_app.logger.error(
            f"API Error: {error.message}",
            extra={
                'error_code': error.error_code,
                'status_code': error.status_code,
                'details': error.details,
                'traceback': traceback.format_exc()
            }
        )
    else:
        current_app.logger.error(
            f"API Error [{error.error_code}]: {error.message}",
            extra={
                'error_code': error.error_code,
                'status_code': error.status_code
            }
        )
    
    return jsonify(error.to_dict()), error.status_code


def handle_domain_error(error: DomainError) -> Tuple[str, int]:
    """
    Maneja un error de dominio y retorna respuesta apropiada.
    
    Args:
        error: Error de dominio
        
    Returns:
        Tuple[str, int]: (respuesta, código de estado)
    """
    from flask import current_app
    from app.application.exceptions.app_exceptions import BadRequestError, ForbiddenError
    
    # Mapear errores de dominio a errores de API
    error_mapping = {
        'ShiftNotOpenError': ForbiddenError,
        'ShiftAlreadyOpenError': BadRequestError,
        'FraudDetectedError': ForbiddenError,
        'DeliveryValidationError': BadRequestError,
    }
    
    error_class_name = error.__class__.__name__
    api_error_class = error_mapping.get(error_class_name, BadRequestError)
    
    api_error = api_error_class(
        message=str(error),
        user_message=str(error)
    )
    
    current_app.logger.warning(f"Domain Error: {error_class_name} - {str(error)}")
    
    if is_json_request():
        return handle_api_error(api_error)
    else:
        flash(str(error), "error")
        return redirect(url_for('routes.scanner')), 302


def handle_validation_error(error: Exception) -> Tuple[str, int]:
    """
    Maneja errores de validación.
    
    Args:
        error: Error de validación
        
    Returns:
        Tuple[str, int]: (respuesta, código de estado)
    """
    from flask import current_app
    from app.application.exceptions.app_exceptions import ValidationError as AppValidationError
    
    # Convertir errores de validadores a ValidationError de aplicación
    if isinstance(error, (SaleIdValidationError, InputValidationError, QuantityValidationError)):
        api_error = AppValidationError(
            message=str(error),
            user_message=str(error)
        )
    else:
        api_error = AppValidationError(
            message=str(error),
            user_message=f"Error de validación: {str(error)}"
        )
    
    current_app.logger.warning(f"Validation Error: {str(error)}")
    
    if is_json_request():
        return handle_api_error(api_error)
    else:
        flash(str(error), "error")
        # Intentar redirigir a la página anterior o al scanner
        return redirect(request.referrer or url_for('routes.scanner')), 302


def handle_http_exception(error: Exception) -> Tuple[str, int]:
    """
    Maneja excepciones HTTP estándar (404, 500, etc.).
    
    Args:
        error: Excepción HTTP
        
    Returns:
        Tuple[str, int]: (respuesta, código de estado)
    """
    from werkzeug.exceptions import HTTPException
    from flask import current_app
    from app.application.exceptions.app_exceptions import NotFoundError, InternalServerError
    
    if isinstance(error, HTTPException):
        status_code = error.code
        
        if status_code == 404:
            api_error = NotFoundError(resource="Recurso")
        elif status_code == 500:
            api_error = InternalServerError()
        else:
            api_error = InternalServerError(
                message=f"Error HTTP {status_code}: {error.description}",
                user_message=error.description
            )
    else:
        api_error = InternalServerError()
    
    current_app.logger.error(f"HTTP Exception: {error}")
    
    if is_json_request():
        return handle_api_error(api_error)
    else:
        from flask import session
        if status_code == 404:
            flash("Recurso no encontrado", "error")
        else:
            flash("Ocurrió un error. Por favor, intenta nuevamente.", "error")
        # CRITICAL: NO redirigir a scanner si hay sesión admin activa
        if session.get('admin_logged_in'):
            return redirect(url_for('routes.admin_dashboard')), 302
        return redirect(url_for('routes.scanner')), 302


def handle_generic_error(error: Exception) -> Tuple[str, int]:
    """
    Maneja errores genéricos no capturados.
    
    Args:
        error: Excepción genérica
        
    Returns:
        Tuple[str, int]: (respuesta, código de estado)
    """
    from flask import current_app
    from app.application.exceptions.app_exceptions import InternalServerError
    
    # Log completo del error
    current_app.logger.error(
        f"Unhandled Error: {type(error).__name__} - {str(error)}",
        exc_info=True,
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
    )
    
    api_error = InternalServerError(
        message=f"Error inesperado: {type(error).__name__} - {str(error)}",
        user_message="Ocurrió un error inesperado. Por favor, intenta nuevamente."
    )
    
    if is_json_request():
        return handle_api_error(api_error)
    else:
        from flask import session
        flash("Ocurrió un error inesperado. Por favor, intenta nuevamente.", "error")
        # CRITICAL: NO redirigir a scanner si hay sesión admin activa
        if session.get('admin_logged_in'):
            return redirect(url_for('routes.admin_dashboard')), 302
        return redirect(url_for('routes.scanner')), 302


def register_error_handlers(app: Flask):
    """
    Registra todos los handlers de errores en la aplicación Flask.
    
    Args:
        app: Aplicación Flask
    """
    
    @app.errorhandler(APIError)
    def handle_api_error_handler(error: APIError):
        """Handler para errores de API"""
        return handle_api_error(error)
    
    @app.errorhandler(DomainError)
    def handle_domain_error_handler(error: DomainError):
        """Handler para errores de dominio"""
        return handle_domain_error(error)
    
    @app.errorhandler(SaleIdValidationError)
    @app.errorhandler(InputValidationError)
    @app.errorhandler(QuantityValidationError)
    def handle_validation_error_handler(error: Exception):
        """Handler para errores de validación"""
        return handle_validation_error(error)
    
    @app.errorhandler(404)
    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_generic_error_handler(error: Exception):
        """Handler genérico para errores no capturados"""
        # Si es HTTPException, usar handler específico
        from werkzeug.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return handle_http_exception(error)
        else:
            return handle_generic_error(error)

