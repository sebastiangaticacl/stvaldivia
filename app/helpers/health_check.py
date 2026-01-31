"""
Health check utilities para el sistema
Verifica el estado de componentes críticos
"""
from typing import Dict, Any, List
from flask import current_app
from .logger import get_logger
from .service_status import get_all_services_status, check_api_status
from .cache_utils import get_cache_info
from app.infrastructure.rate_limiter import RateLimiter

logger = get_logger(__name__)


def get_system_health() -> Dict[str, Any]:
    """
    Obtiene el estado de salud general del sistema
    
    Returns:
        dict con estado de salud de todos los componentes
    """
    health = {
        'status': 'unknown',
        'timestamp': None,
        'components': {},
        'overall_healthy': False
    }
    
    try:
        from datetime import datetime
        health['timestamp'] = datetime.now().isoformat()
        
        # Verificar servicios del sistema
        services = get_all_services_status()
        health['components']['services'] = {
            'status': 'ok' if all(
                s.get('running') or s.get('online') 
                for s in services.values()
            ) else 'degraded',
            'details': services
        }
        
        # Verificar API externa
        api_status = check_api_status()
        health['components']['external_api'] = {
            'status': 'ok' if api_status.get('online') else 'error',
            'details': api_status
        }
        
        # Verificar cache
        try:
            cache_info = get_cache_info()
            health['components']['cache'] = {
                'status': 'ok',
                'details': cache_info['stats']
            }
        except Exception as e:
            health['components']['cache'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Verificar configuración
        config_status = _check_configuration()
        health['components']['configuration'] = config_status
        
        # Determinar estado general
        component_statuses = [
            c.get('status') for c in health['components'].values()
        ]
        
        if all(s == 'ok' for s in component_statuses):
            health['status'] = 'healthy'
            health['overall_healthy'] = True
        elif any(s == 'error' for s in component_statuses):
            health['status'] = 'unhealthy'
            health['overall_healthy'] = False
        else:
            health['status'] = 'degraded'
            health['overall_healthy'] = False
        
        return health
        
    except Exception as e:
        logger.error(f"Error al obtener health check: {e}", exc_info=True)
        health['status'] = 'error'
        health['error'] = str(e)
        return health


def _check_configuration() -> Dict[str, Any]:
    """Verifica que la configuración esté completa"""
    try:
        config = current_app.config if current_app else {}
        
        required_keys = [
            'API_KEY',
            'BASE_API_URL',
            'SECRET_KEY'
        ]
        
        missing = []
        present = []
        
        for key in required_keys:
            if not config.get(key):
                missing.append(key)
            else:
                present.append(key)
        
        return {
            'status': 'ok' if not missing else 'warning',
            'present': present,
            'missing': missing
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def get_health_summary() -> Dict[str, Any]:
    """
    Retorna un resumen breve del estado de salud
    
    Returns:
        dict con resumen del estado
    """
    health = get_system_health()
    
    return {
        'status': health['status'],
        'healthy': health['overall_healthy'],
        'components_count': len(health['components']),
        'components_ok': sum(
            1 for c in health['components'].values() 
            if c.get('status') == 'ok'
        ),
        'timestamp': health['timestamp']
    }














