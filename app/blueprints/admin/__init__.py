"""
Blueprint para rutas administrativas del Bot de IA
"""
from flask import Blueprint

# El prefijo se agregará al registrar el blueprint en __init__.py
admin_bp = Blueprint('admin', __name__)

from . import bot_routes
from . import routes
from . import payment_machines_routes  # Importar routes para endpoints como /api/getnet/status


