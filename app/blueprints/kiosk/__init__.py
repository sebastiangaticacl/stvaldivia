"""
Blueprint para el sistema de Kiosko
"""
from flask import Blueprint

kiosk_bp = Blueprint('kiosk', __name__, url_prefix='/kiosk', template_folder='../../../templates/kiosk')

from . import routes





