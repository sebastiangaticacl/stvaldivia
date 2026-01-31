"""
Servicio para gestión de notificaciones en tiempo real
"""
from typing import Optional, Dict, Any, List
from app.models.notification_models import Notification
from app.helpers.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Servicio para crear y gestionar notificaciones"""
    
    # Tipos de notificaciones
    TYPE_CIERRE_PENDIENTE = 'cierre_pendiente'
    TYPE_DIFERENCIA_GRANDE = 'diferencia_grande'
    TYPE_FRAUDE = 'fraude'
    TYPE_TURNO_ABIERTO = 'turno_abierto'
    TYPE_TURNO_CERRADO = 'turno_cerrado'
    TYPE_INFO = 'info'
    TYPE_SUCCESS = 'success'
    TYPE_WARNING = 'warning'
    TYPE_ERROR = 'error'
    
    # Prioridades
    PRIORITY_LOW = 1
    PRIORITY_NORMAL = 2
    PRIORITY_HIGH = 3
    PRIORITY_CRITICAL = 4
    
    @staticmethod
    def create_notification(
        type: str,
        title: str,
        message: str,
        target_user: Optional[str] = None,
        priority: int = 2,
        data: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        emit_socket: bool = True
    ) -> Notification:
        """
        Crea una notificación y opcionalmente la emite por Socket.IO
        
        Args:
            type: Tipo de notificación
            title: Título
            message: Mensaje
            target_user: Usuario destinatario (None = todos los admins)
            priority: Prioridad (1-4)
            data: Datos adicionales
            action_url: URL de acción
            emit_socket: Si debe emitir por Socket.IO
        
        Returns:
            Notification: La notificación creada
        """
        try:
            # Crear notificación en BD
            notification = Notification.create_notification(
                type=type,
                title=title,
                message=message,
                target_user=target_user,
                priority=priority,
                data=data,
                action_url=action_url
            )
            
            # Emitir por Socket.IO si está habilitado
            if emit_socket:
                NotificationService._emit_notification(notification)
            
            logger.info(f"Notificación creada: {type} - {title}")
            return notification
            
        except Exception as e:
            logger.error(f"Error al crear notificación: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _emit_notification(notification: Notification):
        """Emite una notificación por Socket.IO"""
        try:
            from app import socketio
            
            # Emitir a todos los admins o a un usuario específico
            room = f"user_{notification.target_user}" if notification.target_user else "admins"
            
            socketio.emit('new_notification', notification.to_dict(), room=room)
            logger.debug(f"Notificación emitida por Socket.IO a {room}")
            
        except Exception as e:
            logger.error(f"Error al emitir notificación por Socket.IO: {e}", exc_info=True)
    
    @staticmethod
    def notify_cierre_pendiente(cierre_id: int, barra: str, cajero: str):
        """Notifica sobre un cierre de caja pendiente"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_CIERRE_PENDIENTE,
            title='Cierre de Caja Pendiente',
            message=f'{cajero} ha registrado un cierre en {barra}',
            priority=NotificationService.PRIORITY_HIGH,
            data={'cierre_id': cierre_id, 'barra': barra, 'cajero': cajero},
            action_url=f'/admin/cajas'
        )
    
    @staticmethod
    def notify_diferencia_grande(cierre_id: int, barra: str, diferencia: float):
        """Notifica sobre una diferencia grande en cierre de caja"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_DIFERENCIA_GRANDE,
            title='⚠️ Diferencia Grande en Cierre',
            message=f'Diferencia de ${abs(diferencia):,.0f} en {barra}',
            priority=NotificationService.PRIORITY_CRITICAL,
            data={'cierre_id': cierre_id, 'barra': barra, 'diferencia': diferencia},
            action_url=f'/admin/cajas'
        )
    
    @staticmethod
    def notify_fraude_detectado(sale_id: str, bartender: str, fraud_type: str):
        """Notifica sobre un intento de fraude detectado"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_FRAUDE,
            title='🚨 Fraude Detectado',
            message=f'{bartender} intentó entregar ticket {sale_id} ({fraud_type})',
            priority=NotificationService.PRIORITY_CRITICAL,
            data={'sale_id': sale_id, 'bartender': bartender, 'fraud_type': fraud_type},
            action_url=f'/admin/fraud/history'
        )
    
    @staticmethod
    def notify_turno_abierto(jornada_nombre: str, admin: str):
        """Notifica sobre apertura de turno"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_TURNO_ABIERTO,
            title='✅ Turno Abierto',
            message=f'{admin} abrió el turno: {jornada_nombre}',
            priority=NotificationService.PRIORITY_NORMAL,
            data={'jornada_nombre': jornada_nombre, 'admin': admin},
            action_url=f'/admin/turnos'
        )
    
    @staticmethod
    def notify_turno_cerrado(jornada_nombre: str, admin: str, total_ventas: float):
        """Notifica sobre cierre de turno"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_TURNO_CERRADO,
            title='🏁 Turno Cerrado',
            message=f'{admin} cerró el turno: {jornada_nombre} (${total_ventas:,.0f})',
            priority=NotificationService.PRIORITY_NORMAL,
            data={'jornada_nombre': jornada_nombre, 'admin': admin, 'total_ventas': total_ventas},
            action_url=f'/admin/turnos'
        )
    
    @staticmethod
    def notify_info(title: str, message: str, action_url: Optional[str] = None):
        """Notificación informativa"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_INFO,
            title=title,
            message=message,
            priority=NotificationService.PRIORITY_NORMAL,
            action_url=action_url
        )
    
    @staticmethod
    def notify_success(title: str, message: str, action_url: Optional[str] = None):
        """Notificación de éxito"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_SUCCESS,
            title=title,
            message=message,
            priority=NotificationService.PRIORITY_LOW,
            action_url=action_url
        )
    
    @staticmethod
    def notify_warning(title: str, message: str, action_url: Optional[str] = None):
        """Notificación de advertencia"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_WARNING,
            title=title,
            message=message,
            priority=NotificationService.PRIORITY_HIGH,
            action_url=action_url
        )
    
    @staticmethod
    def notify_error(title: str, message: str, action_url: Optional[str] = None):
        """Notificación de error"""
        return NotificationService.create_notification(
            type=NotificationService.TYPE_ERROR,
            title=title,
            message=message,
            priority=NotificationService.PRIORITY_CRITICAL,
            action_url=action_url
        )
    
    @staticmethod
    def get_unread_count(user: Optional[str] = None) -> int:
        """Obtiene el número de notificaciones no leídas"""
        return Notification.get_unread_count(user)
    
    @staticmethod
    def get_recent(user: Optional[str] = None, limit: int = 20, include_read: bool = False) -> List[Notification]:
        """Obtiene las notificaciones recientes"""
        return Notification.get_recent(user, limit, include_read)
    
    @staticmethod
    def mark_as_read(notification_id: int):
        """Marca una notificación como leída"""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.mark_as_read()
    
    @staticmethod
    def mark_all_as_read(user: Optional[str] = None):
        """Marca todas las notificaciones como leídas"""
        Notification.mark_all_as_read(user)
    
    @staticmethod
    def dismiss(notification_id: int):
        """Descarta una notificación"""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.dismiss()
