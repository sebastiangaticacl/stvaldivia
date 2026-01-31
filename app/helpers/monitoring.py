"""
Sistema de monitoreo y métricas de rendimiento
"""

import time
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
from flask import current_app, request
from threading import Lock
import json

# Almacenamiento de métricas en memoria
_metrics = {
    'request_times': deque(maxlen=1000),  # Últimos 1000 requests
    'endpoint_stats': defaultdict(lambda: {'count': 0, 'total_time': 0, 'errors': 0}),
    'error_counts': defaultdict(int),
    'slow_requests': deque(maxlen=100),  # Requests > 1s
}

_metrics_lock = Lock()


def record_request_time(endpoint, duration, status_code=None):
    """Registra el tiempo de respuesta de un request"""
    with _metrics_lock:
        _metrics['request_times'].append({
            'endpoint': endpoint,
            'duration': duration,
            'timestamp': time.time(),
            'status_code': status_code
        })
        
        # Actualizar estadísticas del endpoint
        stats = _metrics['endpoint_stats'][endpoint]
        stats['count'] += 1
        stats['total_time'] += duration
        
        if status_code and status_code >= 400:
            stats['errors'] += 1
            _metrics['error_counts'][f"{endpoint}:{status_code}"] += 1
        
        # Registrar requests lentos
        if duration > 1.0:
            _metrics['slow_requests'].append({
                'endpoint': endpoint,
                'duration': duration,
                'timestamp': datetime.now().isoformat(),
                'status_code': status_code
            })


def monitor_performance(func):
    """Decorator para monitorear el rendimiento de funciones"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = None
        
        try:
            result = func(*args, **kwargs)
            
            # Intentar obtener status_code del resultado
            if hasattr(result, 'status_code'):
                status_code = result.status_code
            elif isinstance(result, tuple) and len(result) > 1:
                status_code = result[1] if isinstance(result[1], int) else None
            
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            endpoint = request.endpoint or func.__name__
            record_request_time(endpoint, duration, status_code)
    
    return wrapper


def get_performance_stats():
    """Obtiene estadísticas de rendimiento"""
    with _metrics_lock:
        request_times = list(_metrics['request_times'])
        
        if not request_times:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0,
                'error_rate': 0,
                'slow_requests_count': len(_metrics['slow_requests']),
                'endpoint_stats': {},
                'recent_errors': []
            }
        
        durations = [r['duration'] for r in request_times]
        durations_sorted = sorted(durations)
        
        total_requests = len(durations)
        avg_time = sum(durations) / total_requests if total_requests > 0 else 0
        min_time = min(durations) if durations else 0
        max_time = max(durations) if durations else 0
        
        # Calcular percentiles
        p95_idx = int(total_requests * 0.95)
        p99_idx = int(total_requests * 0.99)
        p95_time = durations_sorted[p95_idx] if p95_idx < total_requests else max_time
        p99_time = durations_sorted[p99_idx] if p99_idx < total_requests else max_time
        
        # Calcular tasa de errores
        error_count = sum(1 for r in request_times if r.get('status_code', 200) >= 400)
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        # Estadísticas por endpoint
        endpoint_stats = {}
        for endpoint, stats in _metrics['endpoint_stats'].items():
            if stats['count'] > 0:
                endpoint_stats[endpoint] = {
                    'count': stats['count'],
                    'avg_time': stats['total_time'] / stats['count'],
                    'errors': stats['errors'],
                    'error_rate': (stats['errors'] / stats['count'] * 100) if stats['count'] > 0 else 0
                }
        
        # Errores recientes
        recent_errors = []
        for error_key, count in sorted(_metrics['error_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            endpoint, status = error_key.rsplit(':', 1)
            recent_errors.append({
                'endpoint': endpoint,
                'status_code': int(status),
                'count': count
            })
        
        return {
            'total_requests': total_requests,
            'avg_response_time': round(avg_time, 3),
            'min_response_time': round(min_time, 3),
            'max_response_time': round(max_time, 3),
            'p95_response_time': round(p95_time, 3),
            'p99_response_time': round(p99_time, 3),
            'error_rate': round(error_rate, 2),
            'slow_requests_count': len(_metrics['slow_requests']),
            'endpoint_stats': endpoint_stats,
            'recent_errors': recent_errors,
            'slow_requests': list(_metrics['slow_requests'])[-10:]  # Últimos 10
        }


def check_performance_thresholds():
    """Verifica si se exceden umbrales de rendimiento"""
    stats = get_performance_stats()
    alerts = []
    
    # Umbrales de alerta
    if stats['avg_response_time'] > 0.5:
        alerts.append({
            'level': 'warning',
            'message': f"Tiempo promedio de respuesta alto: {stats['avg_response_time']}s"
        })
    
    if stats['p95_response_time'] > 1.0:
        alerts.append({
            'level': 'warning',
            'message': f"P95 de tiempo de respuesta alto: {stats['p95_response_time']}s"
        })
    
    if stats['error_rate'] > 5.0:
        alerts.append({
            'level': 'critical',
            'message': f"Tasa de errores alta: {stats['error_rate']}%"
        })
    
    if stats['slow_requests_count'] > 50:
        alerts.append({
            'level': 'warning',
            'message': f"Muchos requests lentos: {stats['slow_requests_count']}"
        })
    
    return alerts


def reset_metrics():
    """Resetea todas las métricas (útil para testing)"""
    with _metrics_lock:
        _metrics['request_times'].clear()
        _metrics['endpoint_stats'].clear()
        _metrics['error_counts'].clear()
        _metrics['slow_requests'].clear()



