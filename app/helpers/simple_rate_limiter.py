"""
Rate Limiter simple en memoria (sin dependencias externas)
Para producción, puede reemplazarse por Redis u otro sistema distribuido
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple
from collections import defaultdict
import threading


class SimpleRateLimiter:
    """
    Rate limiter simple en memoria.
    NO es thread-safe para múltiples procesos, pero funciona para single-process Flask.
    """
    
    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def check_rate_limit(self, identifier: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Verifica si un identificador (IP) excedió el rate limit.
        
        Args:
            identifier: Identificador único (ej: IP address)
            max_requests: Número máximo de requests permitidos
            window_seconds: Ventana de tiempo en segundos
        
        Returns:
            Tuple[bool, int]: (is_allowed, remaining_requests)
            - is_allowed: True si está permitido, False si excedió
            - remaining_requests: Requests restantes en la ventana
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        with self._lock:
            # Limpiar requests antiguos
            self._requests[identifier] = [
                ts for ts in self._requests[identifier] 
                if ts > cutoff
            ]
            
            # Contar requests en la ventana
            request_count = len(self._requests[identifier])
            
            if request_count >= max_requests:
                return False, 0
            
            # Agregar este request
            self._requests[identifier].append(now)
            
            remaining = max_requests - request_count - 1
            return True, remaining
    
    def reset(self, identifier: str = None):
        """
        Resetea el rate limit para un identificador o todos.
        
        Args:
            identifier: Identificador específico o None para resetear todos
        """
        with self._lock:
            if identifier:
                self._requests.pop(identifier, None)
            else:
                self._requests.clear()


# Instancia global del rate limiter
_rate_limiter = SimpleRateLimiter()


def check_rate_limit(identifier: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
    """
    Función helper para verificar rate limit.
    
    Args:
        identifier: Identificador único (ej: IP address)
        max_requests: Número máximo de requests permitidos
        window_seconds: Ventana de tiempo en segundos
    
    Returns:
        Tuple[bool, int]: (is_allowed, remaining_requests)
    """
    return _rate_limiter.check_rate_limit(identifier, max_requests, window_seconds)

