"""
Blueprint para el sistema de Caja
"""
from flask import Blueprint

caja_bp = Blueprint('caja', __name__, url_prefix='/caja')

from . import routes
from .views import auth
from .views import register as register_views
from .views import sales
from .views import payment_intents

