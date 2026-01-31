"""
Guard/Middleware: Validación de Turno Abierto
Centraliza la lógica de validación de turno abierto.
"""
from functools import wraps
from flask import redirect, url_for, flash, request, jsonify
from app.application.services.service_factory import get_shift_service
from app.domain.exceptions import ShiftNotOpenError


def require_shift_open(func):
    """
    Decorador para requerir que haya un turno abierto antes de ejecutar la función.
    
    Si no hay turno abierto:
    - Para peticiones JSON: retorna error JSON 403
    - Para peticiones HTML: redirige con mensaje de error
    
    Uso:
        @bp.route('/entregar')
        @require_shift_open
        def entregar():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        shift_service = get_shift_service()
        
        try:
            # Verificar turno usando el servicio (ahora usa Jornada primero)
            is_open = shift_service.is_shift_open()
            
            if not is_open:
                error_message = "No hay un turno abierto. Abre un turno antes de realizar esta operación."
                
                # Si es una petición JSON (API), retornar JSON
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'error': error_message,
                        'code': 'SHIFT_NOT_OPEN'
                    }), 403
                
                # Si es una petición HTML, redirigir con mensaje
                flash(error_message, "error")
                return redirect(url_for('routes.admin_dashboard'))
        except Exception as e:
            # En caso de error al verificar el turno, loguear pero permitir continuar
            # para evitar bloquear el sistema si hay problemas
            from flask import current_app
            current_app.logger.error(f"Error verificando turno abierto: {e}", exc_info=True)
            # En modo desarrollo, permitir continuar para debugging
            # En producción, podrías querer bloquear aquí
        
        return func(*args, **kwargs)
    
    return wrapper


def shift_open_required(func):
    """
    Alias de require_shift_open para mayor claridad semántica.
    """
    return require_shift_open(func)









