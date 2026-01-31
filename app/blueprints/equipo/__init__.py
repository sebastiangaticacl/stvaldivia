"""
Blueprint para la gestión de Equipo
Módulo especializado para gestión de miembros del equipo, turnos y sueldos
"""
from flask import Blueprint

equipo_bp = Blueprint('equipo', __name__, url_prefix='/admin/equipo', template_folder='templates')

from . import routes



