"""
Helper para gestionar cierres de caja
Maneja concurrencia con bloqueo de archivos para evitar race conditions
"""
import os
import json
import fcntl
import platform
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)

# Tolerancia para considerar caja cuadrada
BALANCE_TOLERANCE = 100.0


def _get_closes_file_path() -> str:
    """Obtiene la ruta del archivo de cierres de caja"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de cierres de caja desde archivo")
    instance_dir = get_safe_instance_path() or current_app.instance_path
    return os.path.join(instance_dir, 'register_closes.json')


def _lock_file(file_handle):
    """Bloquea un archivo para escritura exclusiva"""
    system = platform.system()
    if system in ['Linux', 'Darwin']:
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        except (IOError, OSError) as e:
            logger.warning(f"No se pudo bloquear archivo: {e}")
    elif system == 'Windows':
        try:
            import msvcrt
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
        except (IOError, OSError) as e:
            logger.warning(f"No se pudo bloquear archivo en Windows: {e}")


def _unlock_file(file_handle):
    """Libera el bloqueo de un archivo"""
    system = platform.system()
    if system in ['Linux', 'Darwin']:
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except:
            pass
    elif system == 'Windows':
        try:
            import msvcrt
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except:
            pass


def load_register_closes() -> List[Dict[str, Any]]:
    """Carga todos los cierres de caja desde el archivo (con bloqueo)"""
    closes_file = _get_closes_file_path()
    
    if not os.path.exists(closes_file):
        return []
    
    try:
        with open(closes_file, 'r', encoding='utf-8') as f:
            _lock_file(f)
            try:
                closes_list = json.load(f)
            finally:
                _unlock_file(f)
        
        if not isinstance(closes_list, list):
            return []
        
        return closes_list
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error al cargar cierres de caja: {e}")
        return []


def save_register_close(close_data: Dict[str, Any]) -> bool:
    """Guarda un nuevo cierre de caja de forma segura (con bloqueo)"""
    closes_file = _get_closes_file_path()
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(closes_file), exist_ok=True)
    
    try:
        # Leer cierres existentes con bloqueo
        closes_list = []
        if os.path.exists(closes_file):
            with open(closes_file, 'r+', encoding='utf-8') as f:
                _lock_file(f)
                try:
                    closes_list = json.load(f)
                    if not isinstance(closes_list, list):
                        closes_list = []
                except json.JSONDecodeError:
                    closes_list = []
                finally:
                    _unlock_file(f)
        
        # Agregar nuevo cierre
        closes_list.append(close_data)
        
        # Escribir con bloqueo
        with open(closes_file, 'w', encoding='utf-8') as f:
            _lock_file(f)
            try:
                json.dump(closes_list, f, indent=2, ensure_ascii=False)
            finally:
                _unlock_file(f)
        
        logger.info(f"✅ Cierre de caja guardado: {close_data.get('register_name')} - {close_data.get('employee_name')}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar cierre de caja: {e}")
        return False


def update_register_close(register_id: str, closed_at: str, updates: Dict[str, Any]) -> bool:
    """Actualiza un cierre de caja existente de forma segura (con bloqueo)"""
    closes_file = _get_closes_file_path()
    
    if not os.path.exists(closes_file):
        return False
    
    try:
        # Leer cierres existentes con bloqueo
        with open(closes_file, 'r+', encoding='utf-8') as f:
            _lock_file(f)
            try:
                closes_list = json.load(f)
                if not isinstance(closes_list, list):
                    return False
            except json.JSONDecodeError:
                return False
            finally:
                _unlock_file(f)
        
        # Buscar y actualizar cierre
        found = False
        for close in closes_list:
            if close.get('register_id') == register_id and close.get('closed_at') == closed_at:
                close.update(updates)
                found = True
                break
        
        if not found:
            return False
        
        # Escribir con bloqueo
        with open(closes_file, 'w', encoding='utf-8') as f:
            _lock_file(f)
            try:
                json.dump(closes_list, f, indent=2, ensure_ascii=False)
            finally:
                _unlock_file(f)
        
        logger.info(f"✅ Cierre de caja actualizado: {register_id} - {closed_at}")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar cierre de caja: {e}")
        return False


def get_pending_closes() -> List[Dict[str, Any]]:
    """Obtiene solo los cierres pendientes de revisión"""
    all_closes = load_register_closes()
    pending = [close for close in all_closes if close.get('status') == 'pending']
    
    # Ordenar por fecha (más recientes primero)
    pending.sort(key=lambda x: x.get('closed_at', ''), reverse=True)
    
    return pending


def get_balanced_closes() -> List[Dict[str, Any]]:
    """Obtiene los cierres cuadrados"""
    all_closes = load_register_closes()
    balanced = [close for close in all_closes if close.get('status') == 'balanced']
    
    # Ordenar por fecha (más recientes primero)
    balanced.sort(key=lambda x: x.get('closed_at', ''), reverse=True)
    
    return balanced


def get_resolved_closes() -> List[Dict[str, Any]]:
    """Obtiene los cierres resueltos por el superadmin"""
    all_closes = load_register_closes()
    resolved = [close for close in all_closes if close.get('status') == 'resolved']
    
    # Ordenar por fecha (más recientes primero)
    resolved.sort(key=lambda x: x.get('closed_at', ''), reverse=True)
    
    return resolved







