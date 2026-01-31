"""
Servicio de monitoreo completo del sistema
Combina health checks y estado de servicios
"""
from typing import Dict, Any, List
from datetime import datetime
from flask import current_app
from app.helpers.timezone_utils import CHILE_TZ
from app.helpers.health_checks import (
    check_database, check_cache, check_external_api, get_all_health_checks
)
from app.helpers.service_status import get_all_services_status, check_api_status
import time


class MonitoringService:
    """Servicio centralizado de monitoreo del sistema"""
    
    def __init__(self):
        self.last_check_time = None
        self.cached_status = None
        self.cache_ttl = 30  # Cache por 30 segundos
    
    def get_all_services_monitoring(self) -> Dict[str, Any]:
        """
        Obtiene el estado completo de todos los servicios del sistema
        
        Returns:
            Dict con estado de todos los servicios y componentes
        """
        # Verificar si tenemos cache válido
        if (self.cached_status and 
            self.last_check_time and 
            (time.time() - self.last_check_time) < self.cache_ttl):
            return self.cached_status
        
        try:
            # Health checks básicos
            health_checks = get_all_health_checks()
            
            # Estado de servicios del sistema
            system_services = get_all_services_status()
            
            # Estado de API externa (si está configurada)
            api_status = check_api_status(checked_by='monitoring', log_connection=False)
            
            # Información del sistema
            system_info = self._get_system_info()
            
            # Métricas de rendimiento
            performance_metrics = self._get_performance_metrics()
            
            # Estado general
            overall_status = self._calculate_overall_status(
                health_checks, system_services, api_status
            )
            
            # Agrupar servicios por categoría
            services_by_category = self._categorize_services(
                health_checks, system_services, api_status
            )
            
            result = {
                'overall_status': overall_status,
                'timestamp': datetime.now(CHILE_TZ).isoformat(),
                'system_info': system_info,
                'health_checks': health_checks,
                'system_services': system_services,
                'external_api': api_status,
                'performance_metrics': performance_metrics,
                'services_by_category': services_by_category,
                'alerts': self._get_alerts(health_checks, system_services, api_status)
            }
            
            # Cachear resultado
            self.cached_status = result
            self.last_check_time = time.time()
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error en monitoreo de servicios: {e}", exc_info=True)
            return {
                'overall_status': 'error',
                'timestamp': datetime.now(CHILE_TZ).isoformat(),
                'error': str(e),
                'message': 'Error al obtener estado de servicios'
            }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Obtiene información general del sistema"""
        import platform
        
        try:
            import psutil
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'memory_used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent if platform.system() != 'Darwin' else None
            }
        except ImportError:
            # psutil no disponible
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'message': 'Información limitada (psutil no disponible)'
            }
        except Exception as e:
            current_app.logger.warning(f"Error al obtener info del sistema: {e}")
            return {
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'error': str(e)
            }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de rendimiento"""
        try:
            metrics = {}
            
            # Tiempo de respuesta de base de datos
            db_check = check_database()
            if 'response_time_ms' in db_check:
                metrics['database_response_time_ms'] = db_check['response_time_ms']
            
            # Tiempo de respuesta de cache
            cache_check = check_cache()
            if 'response_time_ms' in cache_check:
                metrics['cache_response_time_ms'] = cache_check['response_time_ms']
            
            # Tiempo de respuesta de API externa
            api_check = check_external_api()
            if 'response_time_ms' in api_check:
                metrics['api_response_time_ms'] = api_check['response_time_ms']
            
            return metrics
            
        except Exception as e:
            current_app.logger.warning(f"Error al obtener métricas de rendimiento: {e}")
            return {}
    
    def _calculate_overall_status(
        self, 
        health_checks: Dict[str, Any],
        system_services: Dict[str, Any],
        api_status: Dict[str, Any]
    ) -> str:
        """Calcula el estado general del sistema"""
        # Verificar health checks críticos
        critical_checks = ['database']
        for check_name in critical_checks:
            if check_name in health_checks.get('checks', {}):
                check_status = health_checks['checks'][check_name].get('status')
                if check_status != 'healthy':
                    return 'critical'
        
        # Verificar servicios críticos
        critical_services = ['stvaldivia', 'gunicorn', 'nginx']
        for service_name in critical_services:
            if service_name in system_services:
                service = system_services[service_name]
                if not service.get('running', True) and service.get('critical', False):
                    return 'critical'
        
        # Si hay warnings pero no críticos
        if health_checks.get('status') == 'unhealthy':
            return 'warning'
        
        return 'healthy'
    
    def _categorize_services(
        self,
        health_checks: Dict[str, Any],
        system_services: Dict[str, Any],
        api_status: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categoriza servicios por tipo"""
        categories = {
            'database': [],
            'cache': [],
            'application': [],
            'external': [],
            'system': []
        }
        
        # Health checks
        for check_name, check_result in health_checks.get('checks', {}).items():
            if check_name == 'database':
                categories['database'].append({
                    'name': 'Base de Datos',
                    'type': 'database',
                    'status': check_result.get('status', 'unknown'),
                    'message': check_result.get('message', ''),
                    'response_time_ms': check_result.get('response_time_ms'),
                    'icon': '🗄️'
                })
            elif check_name == 'cache':
                categories['cache'].append({
                    'name': 'Cache',
                    'type': 'cache',
                    'status': check_result.get('status', 'unknown'),
                    'message': check_result.get('message', ''),
                    'response_time_ms': check_result.get('response_time_ms'),
                    'icon': '💾'
                })
            elif check_name == 'external_api':
                categories['external'].append({
                    'name': 'API Externa',
                    'type': 'external_api',
                    'status': check_result.get('status', 'unknown'),
                    'message': check_result.get('message', ''),
                    'response_time_ms': check_result.get('response_time_ms'),
                    'icon': '🌐'
                })
        
        # Servicios del sistema
        for service_name, service_info in system_services.items():
            # Omitir servicios opcionales que no están configurados
            if service_info.get('optional') and service_info.get('status') == 'not_configured':
                continue  # No mostrar servicios opcionales no configurados
            
            service_status = service_info.get('status', 'unknown')
            # Normalizar estado: 'active' -> 'active', 'inactive' -> 'inactive', 'not_configured' -> 'not_configured'
            
            if 'gunicorn' in service_name.lower() or 'flask' in service_name.lower() or service_name == 'gunicorn':
                categories['application'].append({
                    'name': 'Flask/Gunicorn' if service_name == 'gunicorn' else service_name,
                    'type': 'application',
                    'status': service_status,
                    'message': service_info.get('message', ''),
                    'icon': '🚀'
                })
            elif 'nginx' in service_name.lower():
                categories['system'].append({
                    'name': 'Nginx',
                    'type': 'system',
                    'status': service_status,
                    'message': service_info.get('message', ''),
                    'icon': '🌐'
                })
            elif service_name == 'api':
                # API externa - solo mostrar si está configurada
                api_status = service_info.get('status', 'error')
                if api_status != 'error' or service_info.get('online') is not False:
                    categories['external'].append({
                        'name': 'API Externa (PHP POS)',
                        'type': 'external_api',
                        'status': 'online' if service_info.get('online') else 'offline',
                        'message': service_info.get('message', ''),
                        'response_time_ms': service_info.get('response_time_ms'),
                        'icon': '🌐'
                    })
            elif service_name == 'postfix':
                # Postfix solo mostrar si está activo (es opcional)
                if service_status == 'active':
                    categories['system'].append({
                        'name': 'Postfix (Email)',
                        'type': 'system',
                        'status': service_status,
                        'message': service_info.get('message', ''),
                        'icon': '📧'
                    })
                # Si está not_configured, no mostrarlo (ya se omite arriba)
            else:
                categories['system'].append({
                    'name': service_name,
                    'type': 'system',
                    'status': service_status,
                    'message': service_info.get('message', ''),
                    'icon': '⚙️'
                })
        
        return categories
    
    def _get_alerts(
        self,
        health_checks: Dict[str, Any],
        system_services: Dict[str, Any],
        api_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Genera alertas basadas en el estado de los servicios"""
        alerts = []
        
        # Alertas de health checks
        for check_name, check_result in health_checks.get('checks', {}).items():
            if check_result.get('status') == 'unhealthy':
                alerts.append({
                    'level': 'error',
                    'service': check_name,
                    'message': check_result.get('message', f'{check_name} no está funcionando'),
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                })
            elif check_result.get('status') == 'not_configured' and check_name == 'external_api':
                alerts.append({
                    'level': 'info',
                    'service': check_name,
                    'message': 'API externa no configurada (modo local)',
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                })
        
        # Alertas de servicios del sistema
        for service_name, service_info in system_services.items():
            if not service_info.get('running', True) and service_info.get('critical', False):
                alerts.append({
                    'level': 'error',
                    'service': service_name,
                    'message': f'Servicio crítico {service_name} no está corriendo',
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                })
        
        return alerts


# Instancia global del servicio
_monitoring_service_instance = None

def get_monitoring_service() -> MonitoringService:
    """Obtiene la instancia global del servicio de monitoreo"""
    global _monitoring_service_instance
    if _monitoring_service_instance is None:
        _monitoring_service_instance = MonitoringService()
    return _monitoring_service_instance

