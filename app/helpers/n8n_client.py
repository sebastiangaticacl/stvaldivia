"""
Cliente para enviar eventos a n8n
Permite que la aplicación envíe eventos a n8n cuando ocurren acciones específicas
"""
import requests
import logging
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app

logger = logging.getLogger(__name__)

# Métricas de webhooks (thread-safe)
_webhook_metrics = {
    'total_sent': 0,
    'total_success': 0,
    'total_failed': 0,
    'total_timeout': 0,
    'last_success_time': None,
    'last_failure_time': None,
    'last_error': None
}
_metrics_lock = threading.Lock()


def _update_metrics(success: bool, error_type: Optional[str] = None, error_msg: Optional[str] = None):
    """Actualiza métricas de webhooks de forma thread-safe"""
    global _webhook_metrics
    with _metrics_lock:
        _webhook_metrics['total_sent'] += 1
        if success:
            _webhook_metrics['total_success'] += 1
            _webhook_metrics['last_success_time'] = datetime.utcnow().isoformat()
        else:
            _webhook_metrics['total_failed'] += 1
            _webhook_metrics['last_failure_time'] = datetime.utcnow().isoformat()
            if error_type == 'timeout':
                _webhook_metrics['total_timeout'] += 1
            if error_msg:
                _webhook_metrics['last_error'] = error_msg


def get_webhook_metrics() -> Dict[str, Any]:
    """Obtiene métricas de webhooks"""
    global _webhook_metrics
    with _metrics_lock:
        return _webhook_metrics.copy()


def _send_to_n8n_sync(event_type: str, data: Dict[str, Any], workflow_id: Optional[str] = None, 
                      max_retries: int = 3, timeout: int = 5) -> bool:
    """
    Envía un evento a n8n de forma síncrona con retry y backoff exponencial
    
    Args:
        event_type: Tipo de evento
        data: Datos del evento
        workflow_id: ID del workflow específico (opcional)
        max_retries: Número máximo de reintentos
        timeout: Timeout en segundos
        
    Returns:
        bool: True si el evento se envió correctamente, False en caso contrario
    """
    # MODO SOLO LOCAL: No conectar a servicios externos
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            logger.debug(f"LOCAL_ONLY activo: no se envía evento a n8n ({event_type})")
            return True
    except Exception:
        # Si no hay contexto Flask u otro error, continuar con el comportamiento normal
        pass

    # Leer configuración desde SystemConfig primero
    try:
        from app.models.system_config_models import SystemConfig
        webhook_url = SystemConfig.get('n8n_webhook_url') or current_app.config.get('N8N_WEBHOOK_URL')
        secret = SystemConfig.get('n8n_webhook_secret') or current_app.config.get('N8N_WEBHOOK_SECRET')
        api_key = SystemConfig.get('n8n_api_key') or current_app.config.get('N8N_API_KEY')
    except:
        webhook_url = current_app.config.get('N8N_WEBHOOK_URL')
        secret = current_app.config.get('N8N_WEBHOOK_SECRET')
        api_key = current_app.config.get('N8N_API_KEY')
    
    if not webhook_url:
        logger.debug("N8N_WEBHOOK_URL no configurada, no se enviará evento a n8n")
        return False
    
    # Si hay workflow_id, agregarlo a la URL
    if workflow_id:
        if webhook_url.endswith('/'):
            webhook_url = f"{webhook_url}{workflow_id}"
        else:
            webhook_url = f"{webhook_url}/{workflow_id}"
    
    payload = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    if secret:
        headers['X-Webhook-Secret'] = secret
    
    if api_key:
        headers['X-API-Key'] = api_key
    
    # Retry con backoff exponencial
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            logger.info(f"Evento enviado a n8n: {event_type} (intento {attempt + 1}/{max_retries})")
            _update_metrics(True)
            return True
        except requests.exceptions.Timeout as e:
            last_error = ('timeout', str(e))
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                logger.warning(f"Timeout enviando evento a n8n (intento {attempt + 1}/{max_retries}), reintentando en {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Timeout enviando evento a n8n después de {max_retries} intentos: {event_type}")
                _update_metrics(False, 'timeout', str(e))
                return False
        except requests.exceptions.RequestException as e:
            last_error = ('request_error', str(e))
            # Para errores 4xx (client errors), no reintentar
            if hasattr(e.response, 'status_code') and 400 <= e.response.status_code < 500:
                logger.error(f"Error del cliente enviando evento a n8n: {event_type}, error: {e}")
                _update_metrics(False, 'client_error', str(e))
                return False
            # Para errores 5xx (server errors), reintentar
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Error del servidor enviando evento a n8n (intento {attempt + 1}/{max_retries}), reintentando en {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error enviando evento a n8n después de {max_retries} intentos: {event_type}, error: {e}")
                _update_metrics(False, 'server_error', str(e))
                return False
        except Exception as e:
            last_error = ('unexpected_error', str(e))
            logger.error(f"Error inesperado enviando evento a n8n: {event_type}, error: {e}")
            _update_metrics(False, 'unexpected_error', str(e))
            return False
    
    # Si llegamos aquí, todos los intentos fallaron
    if last_error:
        _update_metrics(False, last_error[0], last_error[1])
    return False


def send_to_n8n(event_type: str, data: Dict[str, Any], workflow_id: Optional[str] = None, 
                async_mode: bool = True, max_retries: int = 3, timeout: int = 5) -> bool:
    """
    Envía un evento a n8n (síncrono o asíncrono)
    
    Args:
        event_type: Tipo de evento (ej: 'delivery_created', 'inventory_updated', 'shift_closed')
        data: Datos del evento
        workflow_id: ID del workflow específico (opcional)
        async_mode: Si True, envía en un thread separado (no bloquea)
        max_retries: Número máximo de reintentos (default: 3)
        timeout: Timeout en segundos (default: 5)
        
    Returns:
        bool: True si se programó el envío (async) o se envió correctamente (sync), False en caso contrario
    """
    if async_mode:
        # Enviar en un thread separado para no bloquear
        def send_async():
            try:
                _send_to_n8n_sync(event_type, data, workflow_id, max_retries, timeout)
            except Exception as e:
                logger.error(f"Error en envío asíncrono a n8n: {event_type}, error: {e}")
        
        thread = threading.Thread(target=send_async, daemon=True)
        thread.start()
        logger.debug(f"Evento programado para envío asíncrono a n8n: {event_type}")
        return True
    else:
        # Envío síncrono
        return _send_to_n8n_sync(event_type, data, workflow_id, max_retries, timeout)


def send_delivery_created(delivery_id: int, item_name: str, quantity: int, bartender: str, barra: str):
    """
    Envía evento cuando se crea una entrega
    
    Args:
        delivery_id: ID de la entrega
        item_name: Nombre del item
        quantity: Cantidad
        bartender: Nombre del bartender
        barra: Nombre de la barra
    """
    return send_to_n8n('delivery_created', {
        'delivery_id': delivery_id,
        'item_name': item_name,
        'quantity': quantity,
        'bartender': bartender,
        'barra': barra
    })


def send_inventory_updated(ingredient_id: int, ingredient_name: str, quantity: float, location: str):
    """
    Envía evento cuando se actualiza el inventario
    
    Args:
        ingredient_id: ID del ingrediente
        ingredient_name: Nombre del ingrediente
        quantity: Nueva cantidad
        location: Ubicación
    """
    return send_to_n8n('inventory_updated', {
        'ingredient_id': ingredient_id,
        'ingredient_name': ingredient_name,
        'quantity': quantity,
        'location': location
    })


def send_shift_closed(shift_date: str, total_sales: float, total_deliveries: int):
    """
    Envía evento cuando se cierra un turno
    
    Args:
        shift_date: Fecha del turno
        total_sales: Total de ventas
        total_deliveries: Total de entregas
    """
    return send_to_n8n('shift_closed', {
        'shift_date': shift_date,
        'total_sales': total_sales,
        'total_deliveries': total_deliveries
    })


def send_sale_created(sale_id: str, amount: float, payment_method: str, register_id: int):
    """
    Envía evento cuando se crea una venta
    
    Args:
        sale_id: ID de la venta
        amount: Monto de la venta
        payment_method: Método de pago
        register_id: ID de la caja
    """
    return send_to_n8n('sale_created', {
        'sale_id': sale_id,
        'amount': amount,
        'payment_method': payment_method,
        'register_id': register_id
    })


def send_custom_event(event_type: str, data: Dict[str, Any], workflow_id: Optional[str] = None):
    """
    Envía un evento personalizado a n8n
    
    Args:
        event_type: Tipo de evento personalizado
        data: Datos del evento
        workflow_id: ID del workflow específico (opcional)
    """
    return send_to_n8n(event_type, data, workflow_id)

