"""
Rutas de debug para GetNet (solo en desarrollo)
"""
from flask import jsonify, current_app
from . import ecommerce_bp
from app.helpers.getnet_web_helper import get_getnet_config, generate_getnet_auth, get_getnet_auth_headers
import logging

logger = logging.getLogger(__name__)


@ecommerce_bp.route('/debug/getnet-config', methods=['GET'])
def debug_getnet_config():
    """Endpoint de debug para verificar configuración de GetNet"""
    if not current_app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints solo disponibles en modo DEBUG'}), 403
    
    try:
        config = get_getnet_config()
        
        # Ocultar trankey completo por seguridad
        trankey_display = config.get('trankey', '')[:4] + '...' if config.get('trankey') else 'No configurado'
        
        return jsonify({
            'status': 'ok',
            'config': {
                'api_base_url': config.get('api_base_url'),
                'login': config.get('login'),
                'trankey': trankey_display,
                'sandbox': config.get('sandbox'),
            },
            'auth_headers': list(get_getnet_auth_headers().keys()) if get_getnet_auth_headers() else None,
            'auth_test': generate_getnet_auth(config.get('login', ''), config.get('trankey', '')) if config.get('login') and config.get('trankey') else None
        })
    except Exception as e:
        logger.error(f"Error en debug_getnet_config: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@ecommerce_bp.route('/debug/test-getnet-connection', methods=['GET'])
def debug_test_getnet_connection():
    """Endpoint de debug para probar conexión con GetNet"""
    if not current_app.config.get('DEBUG', False):
        return jsonify({'error': 'Debug endpoints solo disponibles en modo DEBUG'}), 403
    
    import requests
    from app.helpers.getnet_web_helper import get_getnet_config, get_getnet_auth_headers
    
    try:
        config = get_getnet_config()
        headers = get_getnet_auth_headers()
        
        if not headers:
            return jsonify({
                'status': 'error',
                'message': 'No se pudieron obtener headers de autenticación',
                'config': {
                    'login': config.get('login'),
                    'trankey': 'configurado' if config.get('trankey') else 'no configurado'
                }
            }), 400
        
        # Probar conexión básica
        test_url = f"{config['api_base_url']}/health"  # Endpoint común de health check
        
        try:
            response = requests.get(test_url, headers=headers, timeout=5)
            return jsonify({
                'status': 'ok',
                'url': test_url,
                'response_status': response.status_code,
                'response_headers': dict(response.headers),
                'response_text': response.text[:500]
            })
        except requests.exceptions.ConnectionError as e:
            return jsonify({
                'status': 'error',
                'message': 'Error de conexión',
                'error': str(e),
                'url': test_url
            }), 500
        except requests.exceptions.Timeout:
            return jsonify({
                'status': 'error',
                'message': 'Timeout al conectar',
                'url': test_url
            }), 500
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'url': test_url
            }), 500
            
    except Exception as e:
        logger.error(f"Error en debug_test_getnet_connection: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

