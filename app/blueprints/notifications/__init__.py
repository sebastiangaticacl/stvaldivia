"""
Blueprint para las rutas de API de notificaciones
"""
from flask import Blueprint, jsonify, request, session
from app.helpers.notification_service import NotificationService
from app.helpers.logger import get_logger

logger = get_logger(__name__)

bp = Blueprint('notifications_api', __name__, url_prefix='/admin/api/notifications')


@bp.route('', methods=['GET'])
def get_notifications():
    """Obtiene las notificaciones del usuario actual"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        # Obtener parámetros
        limit = request.args.get('limit', 20, type=int)
        include_read = request.args.get('include_read', 'false').lower() == 'true'
        
        # Obtener usuario actual (si existe sistema de usuarios)
        user = session.get('admin_username')
        
        # Obtener notificaciones
        notifications = NotificationService.get_recent(
            user=user,
            limit=limit,
            include_read=include_read
        )
        
        # Obtener contador de no leídas
        unread_count = NotificationService.get_unread_count(user=user)
        
        return jsonify({
            'success': True,
            'notifications': [n.to_dict() for n in notifications],
            'unread_count': unread_count,
            'total': len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener notificaciones: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """Obtiene el número de notificaciones no leídas"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        user = session.get('admin_username')
        count = NotificationService.get_unread_count(user=user)
        
        return jsonify({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error al obtener contador de no leídas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:notification_id>/read', methods=['POST'])
def mark_as_read(notification_id):
    """Marca una notificación como leída"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        NotificationService.mark_as_read(notification_id)
        
        return jsonify({
            'success': True,
            'message': 'Notificación marcada como leída'
        })
        
    except Exception as e:
        logger.error(f"Error al marcar notificación como leída: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/read-all', methods=['POST'])
def mark_all_as_read():
    """Marca todas las notificaciones como leídas"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        user = session.get('admin_username')
        NotificationService.mark_all_as_read(user=user)
        
        return jsonify({
            'success': True,
            'message': 'Todas las notificaciones marcadas como leídas'
        })
        
    except Exception as e:
        logger.error(f"Error al marcar todas como leídas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:notification_id>/dismiss', methods=['POST'])
def dismiss_notification(notification_id):
    """Descarta una notificación"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        NotificationService.dismiss(notification_id)
        
        return jsonify({
            'success': True,
            'message': 'Notificación descartada'
        })
        
    except Exception as e:
        logger.error(f"Error al descartar notificación: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test', methods=['POST'])
def test_notification():
    """Crea una notificación de prueba (solo para desarrollo)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json() or {}
        
        notification_type = data.get('type', 'info')
        title = data.get('title', 'Notificación de Prueba')
        message = data.get('message', 'Esta es una notificación de prueba del sistema')
        priority = data.get('priority', 2)
        
        notification = NotificationService.create_notification(
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            action_url='/admin/dashboard'
        )
        
        return jsonify({
            'success': True,
            'message': 'Notificación de prueba creada',
            'notification': notification.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error al crear notificación de prueba: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
