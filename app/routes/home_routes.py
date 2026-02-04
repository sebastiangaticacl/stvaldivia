"""
Rutas de la Página Principal
"""
from flask import Blueprint, render_template, current_app, request, session, make_response
import os
import hmac
from app.models.jornada_models import Jornada

home_bp = Blueprint('home', __name__)


@home_bp.route('/', methods=['GET', 'POST'])
def index():
    """Página principal - opcionalmente protegida por PIN (MENU_GATE_PIN)"""
    # Gate opcional antes de mostrar el menú principal
    # Preferir variable de entorno para evitar inconsistencias con el reloader
    gate_pin = os.environ.get('MENU_GATE_PIN') or current_app.config.get('MENU_GATE_PIN')
    gate_enabled = bool(gate_pin)

    menu_unlocked = bool(session.get('menu_unlocked') or session.get('admin_logged_in'))

    if gate_enabled and not menu_unlocked:
        error = None
        if request.method == 'POST':
            submitted = (request.form.get('pin') or '').strip()
            if submitted and hmac.compare_digest(submitted, str(gate_pin)):
                session['menu_unlocked'] = True
                # continuar a render normal
            else:
                error = "PIN incorrecto"

        if not session.get('menu_unlocked'):
            resp = make_response(render_template('menu_gate.html', error=error))
            resp.headers['X-MENU-GATE'] = 'enabled'
            resp.headers['X-MENU-UNLOCKED'] = 'false'
            return resp

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
    resp = make_response(render_template('home.html', jornada_abierta=jornada_abierta))
    resp.headers['X-MENU-GATE'] = 'enabled' if gate_enabled else 'disabled'
    resp.headers['X-MENU-UNLOCKED'] = 'true' if (session.get('menu_unlocked') or session.get('admin_logged_in')) else 'false'
    return resp


@home_bp.route('/opera', methods=['GET'])
def opera_landing():
    """Landing estática Ópera — sistema operativo nocturno."""
    return render_template('opera_landing.html')


@home_bp.route('/bimba', methods=['GET'])
def chat_bimba():
    """Página pública para chatear con BIMBA, el agente de IA"""
    return render_template('chat_bimba.html')
