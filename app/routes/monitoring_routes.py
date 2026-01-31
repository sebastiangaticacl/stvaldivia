"""
Rutas para monitoreo y métricas de rendimiento
"""

from flask import Blueprint, jsonify
from datetime import datetime
from app.helpers.monitoring import get_performance_stats, check_performance_thresholds, reset_metrics

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/api/monitoring/stats', methods=['GET'])
def api_monitoring_stats():
    """API: Obtener estadísticas de rendimiento"""
    try:
        stats = get_performance_stats()
        alerts = check_performance_thresholds()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/alerts', methods=['GET'])
def api_monitoring_alerts():
    """API: Obtener alertas de rendimiento"""
    try:
        alerts = check_performance_thresholds()
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@monitoring_bp.route('/api/monitoring/reset', methods=['POST'])
def api_monitoring_reset():
    """API: Resetear métricas (solo para desarrollo/testing)"""
    try:
        reset_metrics()
        return jsonify({
            'success': True,
            'message': 'Métricas reseteadas'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

