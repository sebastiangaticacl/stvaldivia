"""
Utilidades del sistema
Información del sistema, recursos, etc.
"""
import os
import sys
import platform
import psutil
from typing import Dict, Any
from datetime import datetime
from .logger import get_logger

logger = get_logger(__name__)


def get_system_info() -> Dict[str, Any]:
    """
    Obtiene información del sistema
    
    Returns:
        dict con información del sistema
    """
    try:
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'python': {
                'version': sys.version,
                'executable': sys.executable,
                'platform': sys.platform
            },
            'memory': get_memory_info(),
            'disk': get_disk_info(),
            'cpu': get_cpu_info(),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error al obtener info del sistema: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_memory_info() -> Dict[str, Any]:
    """
    Obtiene información de memoria
    
    Returns:
        dict con información de memoria
    """
    try:
        mem = psutil.virtual_memory()
        return {
            'total_gb': round(mem.total / (1024**3), 2),
            'available_gb': round(mem.available / (1024**3), 2),
            'used_gb': round(mem.used / (1024**3), 2),
            'percent': mem.percent,
            'free_gb': round(mem.free / (1024**3), 2)
        }
    except Exception as e:
        logger.error(f"Error al obtener info de memoria: {e}")
        return {'error': str(e)}


def get_disk_info(path: str = '/') -> Dict[str, Any]:
    """
    Obtiene información del disco
    
    Args:
        path: Ruta a verificar (default: '/')
        
    Returns:
        dict con información del disco
    """
    try:
        disk = psutil.disk_usage(path)
        return {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'percent': round((disk.used / disk.total) * 100, 2)
        }
    except Exception as e:
        logger.error(f"Error al obtener info de disco: {e}")
        return {'error': str(e)}


def get_cpu_info() -> Dict[str, Any]:
    """
    Obtiene información de CPU
    
    Returns:
        dict con información de CPU
    """
    try:
        return {
            'count': psutil.cpu_count(logical=True),
            'count_physical': psutil.cpu_count(logical=False),
            'percent': psutil.cpu_percent(interval=1),
            'freq': {
                'current_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'min_mhz': psutil.cpu_freq().min if psutil.cpu_freq() else None,
                'max_mhz': psutil.cpu_freq().max if psutil.cpu_freq() else None
            }
        }
    except Exception as e:
        logger.error(f"Error al obtener info de CPU: {e}")
        return {'error': str(e)}


def get_process_info() -> Dict[str, Any]:
    """
    Obtiene información del proceso actual
    
    Returns:
        dict con información del proceso
    """
    try:
        process = psutil.Process(os.getpid())
        return {
            'pid': process.pid,
            'name': process.name(),
            'status': process.status(),
            'memory_mb': round(process.memory_info().rss / (1024**2), 2),
            'cpu_percent': process.cpu_percent(interval=0.1),
            'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
            'num_threads': process.num_threads()
        }
    except Exception as e:
        logger.error(f"Error al obtener info del proceso: {e}")
        return {'error': str(e)}














