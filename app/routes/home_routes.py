"""
Rutas de la Página Principal
"""
from flask import Blueprint, render_template, current_app
from app.models.jornada_models import Jornada

home_bp = Blueprint('home', __name__)


@home_bp.route('/', methods=['GET', 'POST'])
def index():
    """Página principal - siempre muestra página de inicio"""
    # Verificar si hay un turno abierto (cualquier jornada abierta, no solo de hoy)
    jornada_abierta = None
    try:
        # Buscar cualquier jornada abierta (no solo de hoy)
        # Esto permite reconocer turnos que se abrieron en días anteriores
        jornada_abierta = Jornada.query.filter_by(
            estado_apertura='abierto'
        ).order_by(Jornada.fecha_jornada.desc()).first()
    except Exception as e:
        current_app.logger.error(f"Error al verificar turno abierto: {e}", exc_info=True)
    
    # Siempre mostrar la página de inicio, sin redirecciones automáticas
    return render_template('home.html', jornada_abierta=jornada_abierta)


@home_bp.route('/bimba', methods=['GET'])
def chat_bimba():
    """Página pública para chatear con BIMBA, el agente de IA"""
    return render_template('chat_bimba.html')
