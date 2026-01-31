"""
Circuit Breaker Pattern para APIs externas
Previene sobrecargar APIs cuando están fallando
"""
import time
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
from app.helpers.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"  # Normal, permite solicitudes
    OPEN = "open"  # Bloqueado, rechaza solicitudes
    HALF_OPEN = "half_open"  # Probando si el servicio se recuperó


class CircuitBreaker:
    """
    Circuit Breaker para proteger llamadas a servicios externos
    
    Cuando un servicio falla repetidamente, el circuit breaker se abre
    y rechaza nuevas solicitudes. Después de un tiempo, intenta
    nuevamente (half-open). Si funciona, se cierra nuevamente.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Args:
            failure_threshold: Número de fallos antes de abrir el circuito
            recovery_timeout: Segundos antes de intentar nuevamente
            expected_exception: Tipo de excepción que se considera fallo
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self.last_success_time = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función con protección del circuit breaker
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos de la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerOpenError: Si el circuito está abierto
            Exception: Si la función falla
        """
        # Verificar estado del circuito
        if self.state == CircuitState.OPEN:
            # Verificar si es momento de intentar nuevamente
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit breaker intentando recuperación para {func.__name__}")
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker abierto. Intenta nuevamente en "
                    f"{int(self.recovery_timeout - (time.time() - self.last_failure_time))}s"
                )
        
        # Intentar ejecutar la función
        try:
            result = func(*args, **kwargs)
            self._on_success(func.__name__)
            return result
            
        except self.expected_exception as e:
            self._on_failure(func.__name__, e)
            raise
        
        except Exception as e:
            # Otras excepciones no cuentan como fallo del servicio
            logger.warning(f"Excepción inesperada en {func.__name__}: {e}")
            raise
    
    def _on_success(self, func_name: str):
        """Maneja éxito de la llamada"""
        self.success_count += 1
        self.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Si estamos en half-open y tuvo éxito, cerrar el circuito
            logger.info(f"Circuit breaker cerrado exitosamente para {func_name}")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Si está cerrado y funciona, resetear contador de fallos
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self, func_name: str, error: Exception):
        """Maneja fallo de la llamada"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(
            f"Falló {func_name} (fallos: {self.failure_count}/{self.failure_threshold}): {error}"
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # Si falla en half-open, volver a abrir
            logger.error(f"Circuit breaker vuelve a abrirse para {func_name}")
            self.state = CircuitState.OPEN
            self.failure_count = 0
        elif self.failure_count >= self.failure_threshold:
            # Si alcanza el umbral, abrir el circuito
            logger.error(
                f"Circuit breaker abierto para {func_name} "
                f"después de {self.failure_count} fallos"
            )
            self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Retorna el estado actual del circuit breaker"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'last_success_time': self.last_success_time,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout': self.recovery_timeout
        }
    
    def reset(self):
        """Resetea el circuit breaker manualmente"""
        logger.info("Circuit breaker reseteado manualmente")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None


class CircuitBreakerOpenError(Exception):
    """Excepción cuando el circuit breaker está abierto"""
    pass


# Circuit breakers globales por servicio
_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str, **kwargs) -> CircuitBreaker:
    """
    Obtiene o crea un circuit breaker para un servicio
    
    Args:
        service_name: Nombre del servicio
        **kwargs: Parámetros del circuit breaker
        
    Returns:
        CircuitBreaker para el servicio
    """
    if service_name not in _breakers:
        _breakers[service_name] = CircuitBreaker(**kwargs)
    return _breakers[service_name]


def circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception
):
    """
    Decorador para aplicar circuit breaker a una función
    
    Args:
        service_name: Nombre del servicio
        failure_threshold: Número de fallos antes de abrir
        recovery_timeout: Tiempo antes de intentar nuevamente
        expected_exception: Tipo de excepción que cuenta como fallo
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(
            service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator














