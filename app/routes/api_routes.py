"""
Rutas de API
Endpoints API para servicios, health checks, etc.
"""
from flask import Blueprint, jsonify, request, session, current_app
import requests
import os
from app.helpers.service_status import get_all_services_status, restart_service, get_postfix_queue
from app.helpers.logger import get_logger
from app.infrastructure.rate_limiter.decorators import rate_limit
from app.application.exceptions.app_exceptions import ServiceUnavailableError, InternalServerError
from app.infrastructure.circuit_breaker import _breakers

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = get_logger(__name__)


@api_bp.route('/health')
@rate_limit(max_requests=10, per_seconds=60)
def health_check():
    """Health check básico - mantiene compatibilidad"""
    """Verifica el estado de la conexión con la API"""
    api_key = current_app.config.get('API_KEY')
    base_url = current_app.config.get('BASE_API_URL')
    
    # Diagnóstico detallado
    debug_info = {
        'api_key_set': bool(api_key),
        'api_key_length': len(api_key) if api_key else 0,
        'base_url_set': bool(base_url),
        'base_url': base_url if base_url else None,
        'env_loaded': bool(os.environ.get('API_KEY') or os.environ.get('BASE_API_URL'))
    }
    
    if not api_key or not base_url:
        logger.warning(f"API no configurada. Debug: {debug_info}")
        raise InternalServerError(
            message='API no configurada',
            user_message='La configuración de la API no está completa',
            details={'debug': debug_info if current_app.config.get('DEBUG') else None}
        )
    
    try:
        # Intentar una llamada simple a la API
        url = f"{base_url}/employees"
        headers = {
            "x-api-key": api_key,
            "accept": "application/json"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        
        return jsonify({
            'status': 'ok',
            'message': 'API conectada',
            'online': True,
            'response_time_ms': resp.elapsed.total_seconds() * 1000
        })
    except requests.exceptions.Timeout:
        raise ServiceUnavailableError(
            service="API",
            user_message="La API no responde. Por favor, intenta más tarde."
        )
    except requests.exceptions.RequestException as e:
        raise ServiceUnavailableError(
            service="API",
            user_message=f"Error de conexión con la API: {str(e)}"
        )


@api_bp.route('/system/health', methods=['GET'])
def system_health():
    """Health check completo del sistema"""
    from app.helpers.health_check import get_system_health
    
    try:
        health = get_system_health()
        status_code = 200 if health.get('overall_healthy') else 503
        return jsonify(health), status_code
    except Exception as e:
        logger.error(f"Error en health check: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener estado del sistema: {str(e)}'
        }), 500


@api_bp.route('/system/cache/stats', methods=['GET'])
def cache_stats():
    """Estadísticas del cache"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.cache_utils import get_cache_info
        cache_info = get_cache_info()
        return jsonify(cache_info), 200
    except Exception as e:
        logger.error(f"Error al obtener stats de cache: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al obtener estadísticas: {str(e)}'
        }), 500


@api_bp.route('/system/performance/stats', methods=['GET'])
def performance_stats():
    """Estadísticas de rendimiento de funciones"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.performance_utils import PerformanceMonitor
        stats = PerformanceMonitor.get_stats()
        return jsonify({
            'functions': stats,
            'total_functions': len(stats)
        }), 200
    except Exception as e:
        logger.error(f"Error al obtener stats de rendimiento: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al obtener estadísticas: {str(e)}'
        }), 500


@api_bp.route('/system/csv/stats', methods=['GET'])
def csv_statistics():
    """Estadísticas de archivos CSV"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.csv_optimizer import get_csv_statistics
        from flask import current_app
        
        csv_files = {
            'logs': {
                'path': current_app.config.get('LOG_FILE', ''),
                'header': ['sale_id', 'item_name', 'qty', 'bartender', 'barra', 'timestamp']
            }
        }
        
        stats = {}
        for name, config in csv_files.items():
            if config['path']:
                stats[name] = get_csv_statistics(config['path'], config['header'])
        
        return jsonify({
            'files': stats
        }), 200
    except Exception as e:
        logger.error(f"Error al obtener stats de CSV: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al obtener estadísticas: {str(e)}'
        }), 500


@api_bp.route('/system/info', methods=['GET'])
def system_info():
    """Información del sistema (admin only)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.system_utils import get_system_info, get_process_info
        info = get_system_info()
        info['process'] = get_process_info()
        return jsonify(info), 200
    except Exception as e:
        logger.error(f"Error al obtener info del sistema: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al obtener información: {str(e)}'
        }), 500


@api_bp.route('/system/export/logs', methods=['GET'])
def export_logs():
    """Exporta logs en CSV"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.logs import load_logs
        from app.helpers.export_utils import DataExporter
        
        logs = load_logs()
        return DataExporter.export_logs_csv(logs, "logs")
    except Exception as e:
        logger.error(f"Error al exportar logs: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al exportar: {str(e)}'
        }), 500


@api_bp.route('/system/circuit-breakers', methods=['GET'])
def circuit_breaker_status():
    """Estado de los circuit breakers (admin only)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        breakers_status = {}
        for service_name, breaker in _breakers.items():
            breakers_status[service_name] = breaker.get_state()
        
        return jsonify({
            'breakers': breakers_status,
            'total': len(breakers_status)
        }), 200
    except Exception as e:
        logger.error(f"Error al obtener estado de circuit breakers: {e}", exc_info=True)
        return jsonify({
            'error': f'Error al obtener estado: {str(e)}'
        }), 500


@api_bp.route('/services/status')
def services_status():
    """API endpoint para obtener el estado de los servicios"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        services_status = get_all_services_status()
        return jsonify({
            'status': 'ok',
            'services': services_status
        })
    except Exception as e:
        logger.error(f"Error al obtener estado de servicios: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'services': {
                'postfix': {'status': 'unknown', 'running': False, 'message': 'Error al verificar'},
                'gunicorn': {'status': 'unknown', 'running': False, 'message': 'Error al verificar'},
                'nginx': {'status': 'unknown', 'running': False, 'message': 'Error al verificar'},
                'api': {'status': 'error', 'online': False, 'message': 'Error al verificar'}
            }
        }), 500


@api_bp.route('/services/restart', methods=['POST'])
def restart_service_endpoint():
    """API endpoint para reiniciar un servicio"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        service_name = data.get('service')
        
        if not service_name:
            return jsonify({
                'success': False,
                'message': 'Nombre de servicio no proporcionado'
            }), 400
        
        # Validar que el servicio es uno de los permitidos
        allowed_services = ['postfix', 'gunicorn', 'nginx']
        if service_name not in allowed_services:
            return jsonify({
                'success': False,
                'message': f'Servicio no permitido: {service_name}'
            }), 400
        
        logger.info(f"Intento de reinicio de servicio: {service_name} por usuario admin")
        result = restart_service(service_name)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"Error al reiniciar servicio: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@api_bp.route('/services/postfix/queue')
def postfix_queue():
    """API endpoint para obtener la cola de correo de Postfix"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        queue_data = get_postfix_queue()
        return jsonify(queue_data), 200 if queue_data['success'] else 500
    except Exception as e:
        logger.error(f"Error al obtener cola de Postfix: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'queue': [],
            'total': 0,
            'message': f'Error: {str(e)}'
        }), 500


@api_bp.route('/health/detailed')
@rate_limit(max_requests=5, per_seconds=60)
def detailed_health_check():
    """Health check detallado con todos los componentes"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.health_checks import get_all_health_checks
        health_status = get_all_health_checks()
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    except Exception as e:
        logger.error(f"Error en health check detallado: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@api_bp.route('/dashboard/stats')
def dashboard_stats():
    """API: Estadísticas para el dashboard"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.register_sales_monitor import get_sales_by_register
        from app.helpers.shift_manager_compat import get_shift_status
        
        shift_status = get_shift_status()
        sales_data = get_sales_by_register()
        
        summary = sales_data.get('summary', {})
        
        return jsonify({
            'success': True,
            'shift_open': shift_status.get('is_open', False),
            'total_sales': summary.get('total_sales', 0),
            'total_amount': summary.get('total_amount', 0.0),
            'total_cash': summary.get('total_cash', 0.0),
            'total_debit': summary.get('total_debit', 0.0),
            'total_credit': summary.get('total_credit', 0.0),
            'active_registers': summary.get('total_registers', 0)
        })
    except Exception as e:
        logger.error(f"Error en dashboard/stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener estadísticas: {str(e)}'
        }), 500


@api_bp.route('/sale-details/<sale_id>')
def sale_details(sale_id):
    """Obtiene detalles de una venta"""
    from app.helpers.pos_api import get_entity_details
    import requests
    
    api_key = current_app.config['API_KEY']
    base = current_app.config['BASE_API_URL']
    
    if not api_key:
        return jsonify({'error': 'API no configurada'}), 500
    
    try:
        # Extraer ID numérico si tiene prefijo
        numeric_id = sale_id.replace('BMB ', '').replace('B ', '').strip()
        
        resp = requests.get(
            f"{base}/sales/{numeric_id}",
            headers={"x-api-key": api_key, "accept": "application/json"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Obtener información adicional
        employee_id = data.get("employee_id")
        customer_id = data.get("customer_id")
        register_id = data.get("register_id")
        
        vendedor = "Desconocido"
        comprador = "N/A"
        caja = "Caja desconocida"
        
        if employee_id:
            emp = get_entity_details("employees", employee_id)
            if emp:
                vendedor = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        
        if customer_id:
            cli = get_entity_details("customers", customer_id)
            if cli:
                comprador = f"{cli.get('first_name','')} {cli.get('last_name','')}".strip()
        
        if register_id:
            reg = get_entity_details("registers", register_id)
            if reg:
                caja = reg.get("name", f"Caja ID {register_id}")
        
        return jsonify({
            "sale_id": data.get("sale_id", sale_id),
            "sale_time": data.get("sale_time", "Fecha no disponible"),
            "employee": vendedor,
            "customer": comprador,
            "register": caja,
            "comment": data.get("comment", "")
        })
    except Exception as e:
        logger.error(f"Error al obtener detalles de venta {sale_id}: {e}")
        return jsonify({'error': f'Error al obtener detalles: {str(e)}'}), 500


# ============================================================================
# API v1 - Agent Endpoints
# Endpoints diseñados para consumo de:
# - Agente de IA (BimbaBot)
# - Futura app/web de cartelera
# - Integraciones externas
# ============================================================================

@api_bp.route('/v1/agent/public-info/today', methods=['GET'])
def agent_public_info_today():
    """
    Obtiene información pública del evento de hoy.
    
    Endpoint diseñado para:
    - Agente de IA (BimbaBot) para generar contenido de redes sociales
    - App/web de cartelera para mostrar evento del día
    
    Returns:
        JSON con información pública del evento de hoy o mensaje si no hay evento
    """
    try:
        from app.application.services.programacion_service import ProgramacionService
        
        service = ProgramacionService()
        evento_info = service.get_public_info_for_today()
        
        if evento_info:
            return jsonify({
                'has_event': True,
                'event': evento_info
            }), 200
        else:
            return jsonify({
                'has_event': False,
                'message': 'No hay evento cargado para hoy.'
            }), 200
    except Exception as e:
        logger.error(f"Error en agent/public-info/today: {e}", exc_info=True)
        return jsonify({
            'has_event': False,
            'error': f'Error al obtener información: {str(e)}'
        }), 500


@api_bp.route('/v1/agent/public-info/date', methods=['GET'])
def agent_public_info_date():
    """
    Obtiene información pública del evento para una fecha específica.
    
    Endpoint diseñado para:
    - Agente de IA (BimbaBot) para consultar eventos futuros
    - App/web de cartelera para mostrar eventos por fecha
    
    Query params:
        fecha: Fecha en formato YYYY-MM-DD (requerido)
    
    Returns:
        JSON con información pública del evento o mensaje si no hay evento
    """
    try:
        from app.application.services.programacion_service import ProgramacionService
        from datetime import datetime
        
        fecha_str = request.args.get('fecha')
        if not fecha_str:
            return jsonify({
                'has_event': False,
                'error': 'Parámetro "fecha" requerido (formato: YYYY-MM-DD)'
            }), 400
        
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'has_event': False,
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400
        
        service = ProgramacionService()
        evento_info = service.get_public_info_for_fecha(fecha)
        
        if evento_info:
            return jsonify({
                'has_event': True,
                'event': evento_info
            }), 200
        else:
            return jsonify({
                'has_event': False,
                'message': f'No hay evento cargado para la fecha {fecha_str}.'
            }), 200
    except Exception as e:
        logger.error(f"Error en agent/public-info/date: {e}", exc_info=True)
        return jsonify({
            'has_event': False,
            'error': f'Error al obtener información: {str(e)}'
        }), 500


@api_bp.route('/v1/agent/public-info/upcoming', methods=['GET'])
def agent_public_info_upcoming():
    """
    Obtiene lista de eventos futuros (solo información pública).
    
    Endpoint diseñado para:
    - Agente de IA (BimbaBot) para planificar contenido futuro
    - App/web de cartelera para mostrar próximos eventos
    
    Query params:
        limit: Número máximo de eventos a devolver (default: 10)
    
    Returns:
        JSON con lista de eventos futuros ordenados por fecha ascendente
    """
    try:
        from app.application.services.programacion_service import ProgramacionService
        
        limit = request.args.get('limit', type=int) or 10
        
        # Validar límite
        if limit < 1 or limit > 50:
            limit = 10
        
        service = ProgramacionService()
        eventos = service.get_upcoming_events(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(eventos),
            'events': eventos
        }), 200
    except Exception as e:
        logger.error(f"Error en agent/public-info/upcoming: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener eventos: {str(e)}',
            'events': []
        }), 500


@api_bp.route('/v1/agent/programacion/month/public', methods=['GET'])
def agent_programacion_month_public():
    """
    Obtiene eventos de un mes específico (solo información pública).
    
    Endpoint diseñado para:
    - App/web de cartelera para mostrar programación mensual
    - Integraciones externas que necesitan calendario público
    
    Query params:
        year: Año (requerido)
        month: Mes 1-12 (requerido)
    
    Returns:
        JSON con lista de eventos del mes (solo campos públicos)
    """
    try:
        from app.application.services.programacion_service import ProgramacionService
        
        año = request.args.get('year', type=int)
        mes = request.args.get('month', type=int)
        
        if not año or not mes:
            return jsonify({
                'success': False,
                'error': 'Parámetros "year" y "month" requeridos'
            }), 400
        
        if mes < 1 or mes > 12:
            return jsonify({
                'success': False,
                'error': 'Mes debe estar entre 1 y 12'
            }), 400
        
        service = ProgramacionService()
        eventos = service.get_eventos_mes(año, mes)
        
        # Convertir a formato público
        eventos_publicos = [evento.to_public_dict() for evento in eventos]
        
        return jsonify({
            'success': True,
            'year': año,
            'month': mes,
            'count': len(eventos_publicos),
            'events': eventos_publicos
        }), 200
    except Exception as e:
        logger.error(f"Error en agent/programacion/month/public: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener eventos: {str(e)}',
            'events': []
        }), 500


@api_bp.route('/programacion', methods=['GET'])
@rate_limit(max_requests=120, per_seconds=300)
def api_programacion():
    """
    Endpoint público: Obtiene lista de eventos próximos
    Simplificado para uso del bot BIMBA
    """
    try:
        from app.application.services.programacion_service import ProgramacionService
        
        limit = request.args.get('limit', type=int) or 10
        
        service = ProgramacionService()
        eventos = service.get_upcoming_events(limit=limit)
        
        return jsonify(eventos), 200
        
    except Exception as e:
        logger.error(f"Error en /api/programacion: {e}", exc_info=True)
        return jsonify({
            "error": "Error al obtener programación",
            "detalle": str(e)
        }), 500


@api_bp.route('/v1/agent/programacion/month/internal', methods=['GET'])
def agent_programacion_month_internal():
    """
    Obtiene eventos de un mes específico (incluye información interna de gestión).
    
    Endpoint diseñado para:
    - Agente de IA interno para análisis de producción
    - Dashboard administrativo
    - Reportes internos
    
    Requiere autenticación de administrador.
    
    Query params:
        year: Año (requerido)
        month: Mes 1-12 (requerido)
    
    Returns:
        JSON con lista de eventos del mes (campos públicos + internos)
    """
    # Verificar autenticación de administrador
    if not session.get('admin_logged_in'):
        return jsonify({
            'success': False,
            'error': 'No autorizado. Se requiere autenticación de administrador.'
        }), 401
    
    try:
        from app.application.services.programacion_service import ProgramacionService
        
        año = request.args.get('year', type=int)
        mes = request.args.get('month', type=int)
        
        if not año or not mes:
            return jsonify({
                'success': False,
                'error': 'Parámetros "year" y "month" requeridos'
            }), 400
        
        if mes < 1 or mes > 12:
            return jsonify({
                'success': False,
                'error': 'Mes debe estar entre 1 y 12'
            }), 400
        
        service = ProgramacionService()
        eventos = service.get_eventos_mes(año, mes)
        
        # Convertir a formato completo (incluye campos internos)
        eventos_completos = [evento.to_dict(include_internal=True) for evento in eventos]
        
        return jsonify({
            'success': True,
            'year': año,
            'month': mes,
            'count': len(eventos_completos),
            'events': eventos_completos
        }), 200
    except Exception as e:
        logger.error(f"Error en agent/programacion/month/internal: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener eventos: {str(e)}',
            'events': []
        }), 500
