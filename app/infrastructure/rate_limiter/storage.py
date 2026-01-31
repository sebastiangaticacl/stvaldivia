"""
Storage para Rate Limiting
Almacenamiento de límites de tasa (puede ser memoria, Redis, etc.)
"""
from typing import Dict, List, Optional
import time
from collections import defaultdict


class RateLimitStorage:
    """Interfaz para almacenamiento de rate limits"""
    
    def increment(self, key: str, window: int) -> int:
        """
        Incrementa el contador para una clave.
        
        Args:
            key: Clave única (ej: IP, endpoint)
            window: Ventana de tiempo en segundos
            
        Returns:
            int: Nuevo contador
        """
        raise NotImplementedError
    
    def get_count(self, key: str, window: int) -> int:
        """
        Obtiene el contador actual para una clave.
        
        Args:
            key: Clave única
            window: Ventana de tiempo en segundos
            
        Returns:
            int: Contador actual
        """
        raise NotImplementedError
    
    def reset(self, key: str):
        """
        Resetea el contador para una clave.
        
        Args:
            key: Clave única
        """
        raise NotImplementedError


class MemoryRateLimitStorage(RateLimitStorage):
    """
    Almacenamiento en memoria para rate limits.
    Simple pero efectivo para aplicaciones pequeñas/medianas.
    """
    
    def __init__(self):
        # Estructura: {key: [(timestamp, count), ...]}
        self._storage: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # Limpiar cada hora
    
    def _cleanup_old_entries(self, current_time: float):
        """Limpia entradas antiguas del storage"""
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        # Limpiar claves vacías y entradas muy antiguas (más de 24 horas)
        cutoff = current_time - 86400
        
        keys_to_delete = []
        for key, timestamps in self._storage.items():
            # Filtrar timestamps antiguos
            self._storage[key] = [ts for ts in timestamps if ts > cutoff]
            
            # Marcar para eliminar si está vacía
            if not self._storage[key]:
                keys_to_delete.append(key)
        
        # Eliminar claves vacías
        for key in keys_to_delete:
            del self._storage[key]
        
        self._last_cleanup = current_time
    
    def increment(self, key: str, window: int) -> int:
        """Incrementa el contador para una clave"""
        current_time = time.time()
        self._cleanup_old_entries(current_time)
        
        # Agregar timestamp actual
        self._storage[key].append(current_time)
        
        # Filtrar timestamps dentro de la ventana
        cutoff = current_time - window
        self._storage[key] = [ts for ts in self._storage[key] if ts > cutoff]
        
        return len(self._storage[key])
    
    def get_count(self, key: str, window: int) -> int:
        """Obtiene el contador actual para una clave"""
        current_time = time.time()
        self._cleanup_old_entries(current_time)
        
        if key not in self._storage:
            return 0
        
        # Filtrar timestamps dentro de la ventana
        cutoff = current_time - window
        timestamps = [ts for ts in self._storage[key] if ts > cutoff]
        self._storage[key] = timestamps
        
        return len(timestamps)
    
    def reset(self, key: str):
        """Resetea el contador para una clave"""
        if key in self._storage:
            del self._storage[key]
    
    def get_remaining_time(self, key: str, window: int) -> float:
        """
        Obtiene el tiempo restante hasta que expiren las solicitudes más antiguas.
        
        Args:
            key: Clave única
            window: Ventana de tiempo en segundos
            
        Returns:
            float: Tiempo restante en segundos
        """
        current_time = time.time()
        
        if key not in self._storage or not self._storage[key]:
            return 0
        
        cutoff = current_time - window
        timestamps = [ts for ts in self._storage[key] if ts > cutoff]
        
        if not timestamps:
            return 0
        
        oldest_timestamp = min(timestamps)
        remaining = window - (current_time - oldest_timestamp)
        
        return max(0, remaining)














