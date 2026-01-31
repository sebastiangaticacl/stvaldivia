"""
Blueprint para el sistema de Ecommerce - Venta de Entradas Express
"""
from flask import Blueprint

ecommerce_bp = Blueprint('ecommerce', __name__, url_prefix='/ecommerce', template_folder='../../../templates/ecommerce')

# Importar routes después de crear el blueprint
from . import routes

# Eximir todo el blueprint de CSRF después de importar routes
# Esto se hace aquí para asegurar que todas las funciones estén cargadas
def exempt_ecommerce_from_csrf():
    """Exime el blueprint de ecommerce de CSRF"""
    try:
        from flask import current_app
        if hasattr(current_app, 'csrf') and current_app.csrf:
            current_app.csrf.exempt(ecommerce_bp)
            # También eximir todas las funciones individuales
            if hasattr(ecommerce_bp, 'view_functions'):
                for view_func in ecommerce_bp.view_functions.values():
                    try:
                        current_app.csrf.exempt(view_func)
                    except:
                        pass
    except:
        pass

