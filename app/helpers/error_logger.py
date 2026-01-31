"""
Helper para logging mejorado y monitoreo de errores
"""
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app, request
import json

logger = logging.getLogger(__name__)


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = 'error'
) -> None:
    """
    Registra un error con contexto completo
    
    Args:
        error: Excepción capturada
        context: Contexto adicional (dict)
        level: Nivel de logging ('error', 'warning', 'critical')
    """
    try:
        error_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'request_info': {}
        }
        
        # Agregar información de la request si está disponible
        if request:
            try:
                error_info['request_info'] = {
                    'method': request.method,
                    'url': request.url,
                    'endpoint': request.endpoint,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'args': dict(request.args),
                    'form': dict(request.form) if request.form else {}
                }
            except:
                pass
        
        # Log según nivel
        log_message = json.dumps(error_info, indent=2, ensure_ascii=False)
        
        if level == 'critical':
            logger.critical(log_message)
        elif level == 'warning':
            logger.warning(log_message)
        else:
            logger.error(log_message)
        
        # También loggear en current_app si está disponible
        if current_app:
            app_logger = current_app.logger
            if level == 'critical':
                app_logger.critical(log_message)
            elif level == 'warning':
                app_logger.warning(log_message)
            else:
                app_logger.error(log_message)
                
    except Exception as e:
        # Fallback si hay error al loggear
        logger.error(f"Error al registrar error: {e}")


def log_api_error(
    endpoint: str,
    error: Exception,
    response_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Registra errores específicos de API
    
    Args:
        endpoint: Endpoint de la API
        error: Excepción
        response_data: Datos de respuesta (si hay)
    """
    context = {
        'api_endpoint': endpoint,
        'response_data': response_data
    }
    log_error(error, context, level='error')


def log_sale_error(
    sale_data: Dict[str, Any],
    error: Exception
) -> None:
    """
    Registra errores específicos de ventas
    
    Args:
        sale_data: Datos de la venta
        error: Excepción
    """
    context = {
        'sale_data': sale_data,
        'operation': 'create_sale'
    }
    log_error(error, context, level='critical')







