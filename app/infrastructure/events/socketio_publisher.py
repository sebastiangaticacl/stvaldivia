"""
Publisher de eventos para desacoplar SocketIO del resto del sistema.
Usa el patrón Publisher para emitir eventos en tiempo real.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from flask import current_app


class EventPublisher(ABC):
    """Interfaz del publisher de eventos"""
    
    @abstractmethod
    def emit_delivery_created(self, delivery_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se crea una entrega"""
        pass
    
    @abstractmethod
    def emit_delivery_deleted(self, delivery_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se elimina una entrega"""
        pass
    
    @abstractmethod
    def emit_all_deliveries_cleared(self) -> None:
        """Emitir evento cuando se limpian todas las entregas"""
        pass
    
    @abstractmethod
    def emit_stats_update(self, stats_data: Dict[str, Any]) -> None:
        """Emitir evento de actualización de estadísticas"""
        pass
    
    @abstractmethod
    def emit_survey_response_created(self, response_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se crea una respuesta de encuesta"""
        pass


class SocketIOEventPublisher(EventPublisher):
    """
    Implementación del publisher usando SocketIO.
    Desacopla el uso de SocketIO del resto del sistema.
    """
    
    def __init__(self, socketio_instance):
        """
        Inicializa el publisher con una instancia de SocketIO
        
        Args:
            socketio_instance: Instancia de flask_socketio.SocketIO
        """
        self.socketio = socketio_instance
    
    def emit_delivery_created(self, delivery_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se crea una entrega"""
        try:
            # Emitir a namespace de logs admin
            self.socketio.emit(
                'new_log',
                {'log_entry': delivery_data},
                namespace='/admin_logs'
            )
            
            # Emitir actualización de stats
            self._emit_stats_update_for_delivery(delivery_data)
            
            # Emitir actualización completa de métricas del dashboard
            self._emit_dashboard_metrics_update()
        except Exception as e:
            current_app.logger.error(f"Error al emitir evento de entrega creada: {e}")
    
    def emit_delivery_deleted(self, delivery_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se elimina una entrega"""
        try:
            self.socketio.emit(
                'log_deleted',
                {'log_entry': delivery_data},
                namespace='/admin_logs'
            )
        except Exception as e:
            current_app.logger.error(f"Error al emitir evento de entrega eliminada: {e}")
    
    def emit_all_deliveries_cleared(self) -> None:
        """Emitir evento cuando se limpian todas las entregas"""
        try:
            self.socketio.emit(
                'all_logs_cleared',
                {},
                namespace='/admin_logs'
            )
        except Exception as e:
            current_app.logger.error(f"Error al emitir evento de limpieza de entregas: {e}")
    
    def emit_stats_update(self, stats_data: Dict[str, Any]) -> None:
        """Emitir evento de actualización de estadísticas"""
        try:
            self.socketio.emit(
                'stats_update',
                stats_data,
                namespace='/admin_stats'
            )
            
            # También emitir actualización completa de métricas del dashboard
            self._emit_dashboard_metrics_update()
        except Exception as e:
            current_app.logger.error(f"Error al emitir evento de actualización de stats: {e}")
    
    def _emit_dashboard_metrics_update(self) -> None:
        """Emitir actualización completa de métricas del dashboard"""
        try:
            from app.helpers.dashboard_metrics_service import get_metrics_service
            metrics_service = get_metrics_service()
            metrics = metrics_service.get_all_metrics(use_cache=False)
            
            self.socketio.emit(
                'metrics_update',
                {'metrics': metrics},
                namespace='/admin_stats'
            )
        except Exception as e:
            current_app.logger.error(f"Error al emitir actualización de métricas del dashboard: {e}")
    
    def emit_survey_response_created(self, response_data: Dict[str, Any]) -> None:
        """Emitir evento cuando se crea una respuesta de encuesta"""
        try:
            self.socketio.emit(
                'survey_response',
                response_data,
                namespace='/encuesta'
            )
        except Exception as e:
            current_app.logger.error(f"Error al emitir evento de respuesta de encuesta: {e}")
    
    def _emit_stats_update_for_delivery(self, delivery_data: Dict[str, Any]) -> None:
        """Emitir actualización de stats específica para una entrega"""
        try:
            from datetime import datetime
            now = datetime.now()
            
            # Obtener categoría del item si está disponible
            item_name = delivery_data.get('item_name', '')
            categoria = None
            
            # Intentar obtener categoría desde stats_service
            try:
                from app.application.services.stats_service import StatsService
                stats_service = StatsService()
                categoria = stats_service._get_item_category(item_name)
            except Exception as e:
                current_app.logger.debug(f"No se pudo obtener categoría para {item_name}: {e}")
            
            stats_data = {
                'timestamp': delivery_data.get('timestamp', now.strftime('%Y-%m-%d %H:%M:%S')),
                'hour': now.hour,
                'type': 'new_delivery',
                'bartender': delivery_data.get('bartender', ''),
                'barra': delivery_data.get('barra', ''),
                'item': item_name,
                'categoria': categoria,  # Nueva: categoría del producto
                'qty': delivery_data.get('qty', 0)
            }
            
            self.emit_stats_update(stats_data)
        except Exception as e:
            current_app.logger.error(f"Error al emitir stats update para entrega: {e}")


class NoOpEventPublisher(EventPublisher):
    """
    Implementación dummy que no hace nada.
    Útil para testing o cuando no se necesita tiempo real.
    """
    
    def emit_delivery_created(self, delivery_data: Dict[str, Any]) -> None:
        pass
    
    def emit_delivery_deleted(self, delivery_data: Dict[str, Any]) -> None:
        pass
    
    def emit_all_deliveries_cleared(self) -> None:
        pass
    
    def emit_stats_update(self, stats_data: Dict[str, Any]) -> None:
        pass
    
    def emit_survey_response_created(self, response_data: Dict[str, Any]) -> None:
        pass





