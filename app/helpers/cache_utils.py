"""
Utilidades avanzadas para el sistema de cache
Incluye limpieza automática, estadísticas y monitoreo
"""
import time
import threading
from typing import Dict, Any
from flask import current_app
from .cache import _cache, _cache_config, get_cache_stats as _get_cache_stats
from .logger import get_logger

logger = get_logger(__name__)


class CacheCleaner:
    """Limpia automáticamente entradas expiradas del cache"""
    
    def __init__(self, interval_seconds: int = 300):  # 5 minutos por defecto
        """
        Args:
            interval_seconds: Intervalo entre limpiezas automáticas
        """
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self._last_cleanup = 0
    
    def start(self):
        """Inicia el hilo de limpieza automática"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        logger.info(f"Cache cleaner iniciado (intervalo: {self.interval}s)")
    
    def stop(self):
        """Detiene el hilo de limpieza automática"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Cache cleaner detenido")
    
    def _cleanup_loop(self):
        """Loop principal de limpieza"""
        while self.running:
            try:
                self.cleanup_expired()
                self._last_cleanup = time.time()
            except Exception as e:
                logger.error(f"Error en limpieza automática de cache: {e}")
            
            # Esperar el intervalo
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    @staticmethod
    def cleanup_expired() -> int:
        """
        Limpia todas las entradas expiradas del cache
        
        Returns:
            Número de entradas eliminadas
        """
        current_time = time.time()
        keys_to_remove = []
        
        for key, (value, cached_time) in _cache.items():
            cache_type = key.split('|')[0]
            ttl = _cache_config.get(cache_type, 60)
            
            if current_time - cached_time >= ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            _cache.pop(key, None)
        
        if keys_to_remove:
            logger.debug(f"Cache limpiado: {len(keys_to_remove)} entradas expiradas eliminadas")
        
        return len(keys_to_remove)
    
    def get_last_cleanup_time(self) -> float:
        """Retorna el tiempo de la última limpieza"""
        return self._last_cleanup


# Instancia global del limpiador
_cache_cleaner = CacheCleaner()


def get_cache_stats() -> Dict[str, Any]:
    """
    Retorna estadísticas detalladas del cache
    
    Returns:
        dict con estadísticas del cache
    """
    current_time = time.time()
    total_keys = len(_cache)
    valid = 0
    expired = 0
    cache_by_type = {}
    total_size_estimate = 0
    
    for key, (value, cached_time) in _cache.items():
        cache_type = key.split('|')[0]
        ttl = _cache_config.get(cache_type, 60)
        age = current_time - cached_time
        
        # Contar por tipo
        if cache_type not in cache_by_type:
            cache_by_type[cache_type] = {
                'count': 0,
                'valid': 0,
                'expired': 0,
                'ttl': ttl
            }
        cache_by_type[cache_type]['count'] += 1
        
        # Estimar tamaño (aproximado)
        try:
            import sys
            total_size_estimate += sys.getsizeof(value) + sys.getsizeof(key)
        except:
            pass
        
        if age < ttl:
            valid += 1
            cache_by_type[cache_type]['valid'] += 1
        else:
            expired += 1
            cache_by_type[cache_type]['expired'] += 1
    
    return {
        'total': total_keys,
        'valid': valid,
        'expired': expired,
        'size_estimate_bytes': total_size_estimate,
        'size_estimate_kb': round(total_size_estimate / 1024, 2),
        'by_type': cache_by_type,
        'config': _cache_config.copy()
    }


def get_cache_info() -> Dict[str, Any]:
    """
    Retorna información general del cache
    
    Returns:
        dict con información del cache
    """
    stats = get_cache_stats()
    cleaner_info = {
        'running': _cache_cleaner.running,
        'interval_seconds': _cache_cleaner.interval,
        'last_cleanup': _cache_cleaner._last_cleanup
    }
    
    return {
        'stats': stats,
        'cleaner': cleaner_info,
        'config': _cache_config.copy()
    }


def start_cache_cleaner():
    """Inicia el limpiador automático de cache"""
    _cache_cleaner.start()


def stop_cache_cleaner():
    """Detiene el limpiador automático de cache"""
    _cache_cleaner.stop()


def cleanup_expired_entries() -> int:
    """
    Limpia entradas expiradas manualmente
    
    Returns:
        Número de entradas eliminadas
    """
    return CacheCleaner.cleanup_expired()














