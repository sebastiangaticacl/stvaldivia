"""
Decorador para validación automática de entrada en rutas
"""
from functools import wraps
from flask import request, jsonify, flash, redirect, url_for
from typing import Callable, Optional
from app.application.validators.sale_id_validator import SaleIdValidationError
from app.application.validators.input_validator import InputValidationError
from app.application.validators.quantity_validator import QuantityValidationError
from app.domain.exceptions import ValidationError


def validate_sale_id(param_name: str = 'sale_id', redirect_on_error: bool = False, redirect_url: Optional[str] = None):
    """
    Decorador para validar sale_id en una ruta.
    
    Args:
        param_name: Nombre del parámetro que contiene el sale_id (puede ser 'sale_id' o 'code')
        redirect_on_error: Si es True, redirige con flash message en lugar de retornar JSON
        redirect_url: URL a la que redirigir en caso de error (si redirect_on_error es True)
    
    Ejemplo:
        @bp.route('/scanner')
        @validate_sale_id(param_name='sale_id', redirect_on_error=True)
        def scanner():
            sale_id = request.validated_sale_id  # Ya validado y normalizado
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app.application.validators import SaleIdValidator
            
            # Obtener el valor del parámetro (puede venir de form, args, o json)
            sale_id = None
            
            if request.is_json:
                data = request.get_json() or {}
                sale_id = data.get(param_name) or data.get('sale_id')
            else:
                sale_id = request.form.get(param_name) or request.form.get('sale_id') or \
                         request.args.get(param_name) or request.args.get('sale_id')
            
            # Si hay sale_id, validarlo
            if sale_id:
                try:
                    canonical, numeric = SaleIdValidator.validate_and_normalize(str(sale_id))
                    # Agregar valores validados al request para uso en la función
                    request.validated_sale_id = canonical
                    request.validated_sale_id_numeric = numeric
                    request.original_sale_id = sale_id
                except SaleIdValidationError as e:
                    error_msg = str(e)
                    
                    if redirect_on_error:
                        flash(f"Error: {error_msg}", "error")
                        redirect_to = redirect_url or url_for('routes.scanner')
                        return redirect(redirect_to)
                    else:
                        return jsonify({
                            'error': error_msg,
                            'code': 'VALIDATION_ERROR'
                        }), 400
            else:
                # Si no hay sale_id, no es error (puede ser una búsqueda vacía)
                request.validated_sale_id = None
                request.validated_sale_id_numeric = None
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def handle_validation_errors(func: Callable):
    """
    Decorador para manejar errores de validación de forma consistente.
    
    Captura errores de validación y los retorna de forma amigable.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (SaleIdValidationError, InputValidationError, QuantityValidationError, ValidationError) as e:
            # Si es una petición JSON, retornar JSON
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': str(e),
                    'code': 'VALIDATION_ERROR'
                }), 400
            
            # Si no, usar flash message y redirigir
            from flask import flash, redirect, url_for
            flash(f"Error de validación: {str(e)}", "error")
            
            # Intentar determinar a dónde redirigir
            if hasattr(request, 'referrer') and request.referrer:
                return redirect(request.referrer)
            else:
                return redirect(url_for('routes.scanner'))
    
    return wrapper














