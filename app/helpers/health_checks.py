"""
Health checks completos para el sistema
"""
from flask import current_app
from app.models import db
from typing import Dict, Any
from datetime import datetime
from app.helpers.timezone_utils import CHILE_TZ
import time


def check_database() -> Dict[str, Any]:
    """Verifica la conexión a la base de datos"""
    try:
        start_time = time.time()
        # Query simple para verificar conexión
        db.session.execute(db.text('SELECT 1'))
        response_time = (time.time() - start_time) * 1000  # ms
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'message': 'Conexión a base de datos OK'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Error de conexión a base de datos'
        }


def check_cache() -> Dict[str, Any]:
    """Verifica el estado del cache"""
    try:
        from app.helpers.thread_safe_cache import _shift_cache
        
        # Test de escritura/lectura
        test_key = '__health_check__'
        test_value = 'test'
        
        start_time = time.time()
        _shift_cache.set(test_key, test_value, ttl=1)
        retrieved = _shift_cache.get(test_key)
        response_time = (time.time() - start_time) * 1000
        
        if retrieved == test_value:
            _shift_cache.delete(test_key)
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'message': 'Cache funcionando correctamente'
            }
        else:
            return {
                'status': 'unhealthy',
                'message': 'Cache no está funcionando correctamente'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Error al verificar cache'
        }


def check_external_api() -> Dict[str, Any]:
    """Verifica la conexión a APIs externas"""
    try:
        api_url = current_app.config.get('BASE_API_URL')
        api_key = current_app.config.get('API_KEY')
        
        if not api_url or not api_key:
            return {
                'status': 'not_configured',
                'message': 'API externa no configurada (modo local)'
            }
        
        # En modo local, no verificar
        if current_app.config.get('LOCAL_ONLY'):
            return {
                'status': 'not_configured',
                'message': 'API externa deshabilitada (LOCAL_ONLY=true)'
            }
        
        # Si está configurada, verificar conectividad básica
        import requests
        start_time = time.time()
        try:
            response = requests.get(f"{api_url}/employees", 
                                  headers={'Authorization': f'Bearer {api_key}'},
                                  timeout=5)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 401, 403]:  # 401/403 significa que la API responde
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2),
                    'message': 'API externa accesible'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'status_code': response.status_code,
                    'message': f'API externa respondió con código {response.status_code}'
                }
        except requests.exceptions.Timeout:
            return {
                'status': 'unhealthy',
                'message': 'Timeout al conectar con API externa'
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'unhealthy',
                'message': 'No se pudo conectar con API externa'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Error al verificar API externa'
        }


def get_all_health_checks() -> Dict[str, Any]:
    """Ejecuta todos los health checks y retorna el estado general"""
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'external_api': check_external_api()
    }
    
    # Estado general: healthy si todos los checks críticos están healthy
    critical_checks = ['database', 'cache']
    all_healthy = all(
        checks[check]['status'] == 'healthy' 
        for check in critical_checks
    )
    
    overall_status = 'healthy' if all_healthy else 'unhealthy'
    
    return {
        'status': overall_status,
        'timestamp': datetime.now(CHILE_TZ).isoformat(),
        'checks': checks
    }





