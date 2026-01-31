"""
Sistema de Logging Consistente
Proporciona funciones para logging estructurado y consistente en toda la aplicación
"""
import logging
import sys
from datetime import datetime
from functools import wraps
from flask import current_app, request


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado con el nombre del módulo
    
    Args:
        name: Nombre del logger (usualmente __name__)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Solo configurar si no tiene handlers (evitar duplicados)
        logger.setLevel(logging.INFO)
        
        # Formato consistente
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def log_request_info(logger: logging.Logger = None):
    """
    Decorador para registrar información de request
    
    Args:
        logger: Logger a usar (opcional)
    
    Returns:
        Decorador
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if logger is None:
                app_logger = get_logger(func.__module__)
            else:
                app_logger = logger
            
            try:
                # Información del request
                app_logger.info(
                    f"Request: {request.method} {request.path} - "
                    f"Endpoint: {func.__name__} - "
                    f"IP: {request.remote_addr} - "
                    f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}"
                )
                
                # Ejecutar función
                result = func(*args, **kwargs)
                
                # Log de éxito
                app_logger.debug(f"Request completado exitosamente: {func.__name__}")
                
                return result
                
            except Exception as e:
                # Log de error
                app_logger.error(
                    f"Error en {func.__name__}: {str(e)} - "
                    f"Request: {request.method} {request.path}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_error(logger: logging.Logger, message: str, error: Exception = None, context: dict = None):
    """
    Registra un error de forma estructurada
    
    Args:
        logger: Logger a usar
        message: Mensaje de error
        error: Excepción (opcional)
        context: Contexto adicional (opcional)
    """
    error_msg = message
    
    if error:
        error_msg += f" - Error: {str(error)}"
        error_msg += f" - Tipo: {type(error).__name__}"
    
    if context:
        context_str = " - ".join([f"{k}: {v}" for k, v in context.items()])
        error_msg += f" - Contexto: {context_str}"
    
    logger.error(error_msg, exc_info=error is not None)


def log_info(logger: logging.Logger, message: str, context: dict = None):
    """
    Registra información de forma estructurada
    
    Args:
        logger: Logger a usar
        message: Mensaje informativo
        context: Contexto adicional (opcional)
    """
    info_msg = message
    
    if context:
        context_str = " - ".join([f"{k}: {v}" for k, v in context.items()])
        info_msg += f" - Contexto: {context_str}"
    
    logger.info(info_msg)


def log_warning(logger: logging.Logger, message: str, context: dict = None):
    """
    Registra una advertencia de forma estructurada
    
    Args:
        logger: Logger a usar
        message: Mensaje de advertencia
        context: Contexto adicional (opcional)
    """
    warning_msg = message
    
    if context:
        context_str = " - ".join([f"{k}: {v}" for k, v in context.items()])
        warning_msg += f" - Contexto: {context_str}"
    
    logger.warning(warning_msg)


def safe_log_error(func):
    """
    Decorador para manejar errores de forma segura y registrar logs
    
    Args:
        func: Función a decorar
    
    Returns:
        Función decorada con manejo de errores
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_error(
                logger,
                f"Error en {func.__name__}",
                error=e,
                context={
                    'args': str(args)[:100],
                    'kwargs_keys': list(kwargs.keys())
                }
            )
            raise
    
    return wrapper








