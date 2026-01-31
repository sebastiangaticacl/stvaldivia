"""
Logging estructurado en JSON
Útil para integración con sistemas de logging (ELK, Splunk, etc.)
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from flask import request


class JSONFormatter(logging.Formatter):
    """Formatter que produce logs en formato JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea un log record como JSON
        
        Args:
            record: Log record a formatear
            
        Returns:
            String JSON con el log
        """
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Agregar información de request si está disponible
        try:
            if request:
                log_data['request'] = {
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'Unknown')[:100]
                }
        except RuntimeError:
            # No hay contexto de Flask
            pass
        
        # Agregar excepción si existe
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Agregar campos extra si existen
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    Logger estructurado que facilita logging con contexto
    """
    
    def __init__(self, name: str, use_json: bool = False):
        """
        Args:
            name: Nombre del logger
            use_json: Si True, usa formato JSON; si False, formato texto
        """
        self.logger = logging.getLogger(name)
        self.use_json = use_json
        
        # Configurar si no tiene handlers
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            
            handler = logging.StreamHandler(sys.stdout)
            
            if use_json:
                handler.setFormatter(JSONFormatter())
            else:
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
            
            self.logger.addHandler(handler)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """Log con contexto adicional"""
        if context:
            # Agregar contexto como campos extra
            extra_fields = {'context': context}
            self.logger.log(level, message, extra={'extra_fields': extra_fields}, exc_info=exc_info)
        else:
            self.logger.log(level, message, exc_info=exc_info)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log nivel info"""
        self._log_with_context(logging.INFO, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None):
        """Log nivel error"""
        self._log_with_context(logging.ERROR, message, context, exc_info)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log nivel warning"""
        self._log_with_context(logging.WARNING, message, context)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log nivel debug"""
        self._log_with_context(logging.DEBUG, message, context)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None):
        """Log nivel critical"""
        self._log_with_context(logging.CRITICAL, message, context, exc_info)


def get_structured_logger(name: str, use_json: bool = False) -> StructuredLogger:
    """
    Obtiene un logger estructurado
    
    Args:
        name: Nombre del logger
        use_json: Si True, usa formato JSON
        
    Returns:
        StructuredLogger configurado
    """
    return StructuredLogger(name, use_json=use_json)














