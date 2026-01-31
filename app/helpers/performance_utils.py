"""
Utilidades para monitoreo y optimización de rendimiento
"""
import time
import functools
from typing import Callable, Any, Dict
from collections import defaultdict
from .logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Monitor de rendimiento para funciones"""
    
    _call_stats: Dict[str, list] = defaultdict(list)
    _call_count: Dict[str, int] = defaultdict(int)
    
    @classmethod
    def track(cls, func_name: str = None):
        """
        Decorador para monitorear el rendimiento de una función
        
        Args:
            func_name: Nombre personalizado (default: nombre de la función)
        """
        def decorator(func: Callable) -> Callable:
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    
                    # Registrar estadísticas
                    cls._call_stats[name].append(elapsed)
                    cls._call_count[name] += 1
                    
                    # Log si es lento (>1 segundo)
                    if elapsed > 1.0:
                        logger.warning(
                            f"Función lenta: {name} tomó {elapsed:.2f}s",
                            extra={'function': name, 'elapsed': elapsed}
                        )
                    
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Error en {name} después de {elapsed:.2f}s: {e}",
                        extra={'function': name, 'elapsed': elapsed, 'error': str(e)}
                    )
                    raise
            
            return wrapper
        return decorator
    
    @classmethod
    def get_stats(cls, func_name: str = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de rendimiento
        
        Args:
            func_name: Nombre de función específica (None = todas)
            
        Returns:
            dict con estadísticas
        """
        if func_name:
            if func_name not in cls._call_stats:
                return {}
            
            times = cls._call_stats[func_name]
            if not times:
                return {}
            
            return {
                'function': func_name,
                'call_count': cls._call_count[func_name],
                'total_time': sum(times),
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'last_time': times[-1] if times else 0
            }
        else:
            # Estadísticas de todas las funciones
            all_stats = {}
            for name in cls._call_stats.keys():
                all_stats[name] = cls.get_stats(name)
            return all_stats
    
    @classmethod
    def clear_stats(cls, func_name: str = None):
        """Limpia las estadísticas"""
        if func_name:
            cls._call_stats[func_name] = []
            cls._call_count[func_name] = 0
        else:
            cls._call_stats.clear()
            cls._call_count.clear()


def time_it(func: Callable) -> Callable:
    """
    Decorador simple para medir tiempo de ejecución
    
    Usage:
        @time_it
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} ejecutado en {elapsed:.3f}s")
        return result
    return wrapper


class BatchProcessor:
    """
    Procesa items en lotes para optimizar operaciones
    """
    
    def __init__(self, batch_size: int = 100):
        """
        Args:
            batch_size: Tamaño del lote
        """
        self.batch_size = batch_size
    
    def process(self, items: list, processor: Callable) -> list:
        """
        Procesa items en lotes
        
        Args:
            items: Lista de items a procesar
            processor: Función que procesa un lote de items
            
        Returns:
            Lista de resultados
        """
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = processor(batch)
            if isinstance(batch_results, list):
                results.extend(batch_results)
            else:
                results.append(batch_results)
        return results














