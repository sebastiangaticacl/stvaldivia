"""
Rutas de debugging - Solo disponibles en desarrollo o con DEBUG_ERRORS=1
"""
import os
from flask import Blueprint, jsonify, request, session, current_app, render_template

debug_bp = Blueprint('debug', __name__, url_prefix='/admin/debug')

def is_debug_errors_enabled():
    """
    Verificar si los endpoints de debug están habilitados.
    Controlado por variable de entorno ENABLE_DEBUG_ERRORS.
    Por defecto: false (deshabilitado en producción).
    """
    enable_flag = os.environ.get('ENABLE_DEBUG_ERRORS', 'false').lower()
    return enable_flag in ('1', 'true', 'yes')

def is_debug_enabled():
    """Verificar si el modo debug está habilitado"""
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production'
    debug_errors = os.environ.get('DEBUG_ERRORS', '0') == '1'
    is_localhost = request.host.startswith('localhost') or request.host.startswith('127.0.0.1')
    
    # Permitir si:
    # 1. No es producción Y es localhost, O
    # 2. DEBUG_ERRORS=1 está configurado, O
    # 3. Usuario admin está logueado (para producción con flag)
    return (not is_production and is_localhost) or debug_errors or session.get('admin_logged_in')

def _return_deprecated_response(route_path):
    """
    Retorna una respuesta HTTP 410 Gone indicando que el endpoint está deprecated.
    Incluye headers apropiados y logging.
    """
    # Extract client IP from X-Forwarded-For (first IP), fallback to remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.remote_addr or 'unknown'
    
    current_app.logger.info(f"DEPRECATED endpoint accessed: {route_path} from IP: {client_ip}")
    
    response = jsonify({
        'error': 'This endpoint has been deprecated',
        'deprecated': True,
        'endpoint': route_path,
        'method': request.method
    })
    response.status_code = 410
    response.headers['X-Deprecated'] = 'true'
    return response


@debug_bp.route('/errors/export', strict_slashes=False)
def export_errors():
    """Exportar reporte de errores capturados en el cliente"""
    # Feature flag: Si ENABLE_DEBUG_ERRORS=false, retornar 410 Gone
    if not is_debug_errors_enabled():
        return _return_deprecated_response(request.path)
    
    if not is_debug_enabled():
        return jsonify({'error': 'Debug mode not enabled'}), 403
    
    # El reporte debe venir del cliente vía POST body
    # Por ahora retornamos instrucciones
    return jsonify({
        'message': 'Use window.getErrorReport() in browser console to get error report',
        'instructions': {
            'get_report': 'window.getErrorReport()',
            'clear_report': 'window.clearErrorReport()',
            'export_json': 'JSON.stringify(window.getErrorReport(), null, 2)'
        }
    })


@debug_bp.route('/errors', methods=['GET', 'POST'], strict_slashes=False)
def errors_handler():
    """Manejar ambos GET y POST para /errors - evita redirects de Flask"""
    # Feature flag: Si ENABLE_DEBUG_ERRORS=false, retornar 410 Gone inmediatamente
    # Esta verificación debe ser la PRIMERA cosa que se ejecute para evitar redirects
    if not is_debug_errors_enabled():
        return _return_deprecated_response(request.path)
    
    # POST: Recibir reporte de errores del cliente
    if request.method == 'POST':
        if not is_debug_enabled():
            return jsonify({'error': 'Debug mode not enabled'}), 403
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Loggear errores críticos
            if data.get('network_errors'):
                for error in data['network_errors']:
                    if error.get('status', 0) >= 500:
                        current_app.logger.error(
                            f"🔴 Network Error 5xx: {error.get('method')} {error.get('url')} → {error.get('status')}"
                        )
            
            if data.get('js_errors'):
                for error in data['js_errors']:
                    current_app.logger.error(
                        f"🔴 JS Error: {error.get('message')} at {error.get('filename')}:{error.get('lineno')}"
                    )
            
            # Retornar resumen
            return jsonify({
                'received': True,
                'summary': {
                    'js_errors': len(data.get('js_errors', [])),
                    'network_errors': len(data.get('network_errors', [])),
                    'csp_violations': len(data.get('csp_violations', [])),
                    'unhandled_rejections': len(data.get('unhandled_rejections', []))
                }
            })
        except Exception as e:
            current_app.logger.error(f"Error receiving error report: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    # GET: Panel simple para ver resumen de errores
    # Mantener verificación de admin auth (no debilitar seguridad)
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Admin login required'}), 403
    
    if not is_debug_enabled():
        return jsonify({'error': 'Debug mode not enabled'}), 403
    
    return render_template('admin/debug_errors.html')

