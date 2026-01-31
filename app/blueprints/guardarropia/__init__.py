"""
Blueprint para la gestión de Guardarropía
Módulo para gestionar el guardado y retiro de prendas/abrigos de clientes
"""
from flask import Blueprint

# Blueprint principal para trabajadores (sin /admin)
guardarropia_bp = Blueprint('guardarropia', __name__, url_prefix='/guardarropia', template_folder='templates')

# Blueprint separado para rutas administrativas
guardarropia_admin_bp = Blueprint('guardarropia_admin', __name__, url_prefix='/admin/guardarropia', template_folder='templates')

from . import routes




