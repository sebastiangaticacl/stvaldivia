"""
Helper para reintentos automáticos en llamadas a API
Mejora la robustez del sistema ante fallos temporales
"""
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorador para reintentar llamadas a API en caso de fallo
    
    Args:
        max_retries: Número máximo de reintentos
        delay: Tiempo de espera inicial entre reintentos (segundos)
        backoff: Factor de multiplicación para el delay
        exceptions: Tupla de excepciones que deben activar el reintento
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Intento {attempt + 1}/{max_retries} falló en {func.__name__}: {e}. "
                            f"Reintentando en {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Todos los intentos fallaron en {func.__name__}: {e}"
                        )
                        raise
                except Exception as e:
                    # Para excepciones no esperadas, no reintentar
                    logger.error(f"Error inesperado en {func.__name__}: {e}")
                    raise
            
            # No debería llegar aquí, pero por si acaso
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_api_call(
    func: Callable,
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs
) -> Any:
    """
    Función helper para reintentar una llamada a API
    
    Args:
        func: Función a ejecutar
        *args: Argumentos posicionales
        max_retries: Número máximo de reintentos
        delay: Tiempo de espera inicial
        backoff: Factor de multiplicación
        **kwargs: Argumentos nombrados
        
    Returns:
        Resultado de la función
    """
    current_delay = delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"Intento {attempt + 1}/{max_retries} falló: {e}. "
                    f"Reintentando en {current_delay}s..."
                )
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"Todos los intentos fallaron: {e}")
                raise
    
    if last_exception:
        raise last_exception







