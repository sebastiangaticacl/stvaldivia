"""
Rate Limiter Principal
Implementa el algoritmo de token bucket / sliding window
"""
from typing import Optional, Callable
import time
from app.infrastructure.rate_limiter.storage import RateLimitStorage, MemoryRateLimitStorage
from app.application.exceptions.app_exceptions import RateLimitError


class RateLimitExceeded(Exception):
    """Excepción cuando se excede el rate limit"""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """
    Rate Limiter usando algoritmo de ventana deslizante (sliding window).
    
    Limita el número de solicitudes por ventana de tiempo.
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        storage: Optional[RateLimitStorage] = None
    ):
        """
        Inicializa el rate limiter.
        
        Args:
            max_requests: Máximo de solicitudes permitidas
            window_seconds: Ventana de tiempo en segundos
            storage: Almacenamiento para los límites (None = usar memoria)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.storage = storage or MemoryRateLimitStorage()
    
    def check(self, key: str) -> bool:
        """
        Verifica si se puede realizar una solicitud.
        
        Args:
            key: Clave única para identificar el límite (ej: IP, endpoint)
            
        Returns:
            bool: True si se permite la solicitud, False si se excede el límite
            
        Raises:
            RateLimitExceeded: Si se excede el límite
        """
        count = self.storage.increment(key, self.window_seconds)
        
        if count > self.max_requests:
            # Calcular tiempo restante
            remaining = self.storage.get_remaining_time(key, self.window_seconds)
            raise RateLimitExceeded(
                f"Rate limit excedido: {count}/{self.max_requests} solicitudes en {self.window_seconds}s",
                retry_after=remaining
            )
        
        return True
    
    def get_remaining(self, key: str) -> int:
        """
        Obtiene el número de solicitudes restantes.
        
        Args:
            key: Clave única
            
        Returns:
            int: Solicitudes restantes
        """
        count = self.storage.get_count(key, self.window_seconds)
        return max(0, self.max_requests - count)
    
    def get_reset_time(self, key: str) -> float:
        """
        Obtiene el tiempo hasta que se resetea el contador.
        
        Args:
            key: Clave única
            
        Returns:
            float: Tiempo en segundos hasta el reset
        """
        return self.storage.get_remaining_time(key, self.window_seconds)
    
    def reset(self, key: str):
        """
        Resetea el contador para una clave.
        
        Args:
            key: Clave única
        """
        self.storage.reset(key)


class APIRateLimiter:
    """
    Rate Limiter específico para proteger APIs externas.
    Previene sobrecarga de servicios externos.
    """
    
    def __init__(self, storage: Optional[RateLimitStorage] = None):
        """
        Inicializa el rate limiter para APIs.
        
        Límites por defecto:
        - 60 solicitudes por minuto
        - 1000 solicitudes por hora
        """
        # Límites por minuto (ventana corta)
        self.per_minute = RateLimiter(
            max_requests=60,
            window_seconds=60,
            storage=storage
        )
        
        # Límites por hora (ventana larga)
        self.per_hour = RateLimiter(
            max_requests=1000,
            window_seconds=3600,
            storage=storage
        )
    
    def check(self, api_name: str = "default") -> bool:
        """
        Verifica si se puede hacer una solicitud a la API.
        
        Args:
            api_name: Nombre de la API (para límites separados)
            
        Returns:
            bool: True si se permite
            
        Raises:
            RateLimitExceeded: Si se excede algún límite
        """
        key_minute = f"api:{api_name}:minute"
        key_hour = f"api:{api_name}:hour"
        
        # Verificar ambos límites
        try:
            self.per_minute.check(key_minute)
            self.per_hour.check(key_hour)
            return True
        except RateLimitExceeded as e:
            # Determinar cuál límite se excedió y usar su retry_after
            try:
                self.per_minute.check(key_minute)
            except RateLimitExceeded as e_min:
                raise e_min
            
            raise e














