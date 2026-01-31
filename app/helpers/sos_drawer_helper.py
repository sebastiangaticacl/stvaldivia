"""
Helper para gestionar solicitudes de apertura de cajón (SOS)
Maneja concurrencia con bloqueo de archivos para evitar race conditions
"""
import os
import json
import fcntl
import platform
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)

# Tiempo de expiración de solicitudes (10 minutos)
EXPIRATION_MINUTES = 10

# Cooldown entre solicitudes (5 minutos)
COOLDOWN_MINUTES = 5

# Límite diario de solicitudes por cajero
DAILY_LIMIT_PER_CASHIER = 10


def _get_sos_file_path() -> str:
    """Obtiene la ruta del archivo de solicitudes SOS"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de solicitudes SOS desde archivo")
    instance_dir = get_safe_instance_path() or current_app.instance_path
    return os.path.join(instance_dir, 'sos_drawer_requests.json')


def _lock_file(file_handle):
    """
    Bloquea un archivo para escritura exclusiva
    Compatible con Linux, macOS y Windows
    """
    system = platform.system()
    if system in ['Linux', 'Darwin']:  # Linux o macOS
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        except (IOError, OSError) as e:
            logger.warning(f"No se pudo bloquear archivo (puede ser normal en algunos sistemas): {e}")
    elif system == 'Windows':
        try:
            import msvcrt
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
        except (IOError, OSError) as e:
            logger.warning(f"No se pudo bloquear archivo en Windows: {e}")
    # Si no se puede bloquear, continuar sin bloqueo (mejor que fallar)


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


def load_sos_requests() -> List[Dict[str, Any]]:
    """
    Carga todas las solicitudes SOS desde el archivo
    Filtra automáticamente las expiradas
    """
    sos_file = _get_sos_file_path()
    
    if not os.path.exists(sos_file):
        return []
    
    try:
        with open(sos_file, 'r', encoding='utf-8') as f:
            _lock_file(f)
            try:
                requests_list = json.load(f)
            finally:
                _unlock_file(f)
        
        if not isinstance(requests_list, list):
            return []
        
        # Filtrar solicitudes expiradas
        now = datetime.now()
        valid_requests = []
        
        for req in requests_list:
            requested_at_str = req.get('requested_at')
            if not requested_at_str:
                continue
            
            try:
                requested_at = datetime.fromisoformat(requested_at_str.replace('Z', '+00:00'))
                # Si es datetime naive, asumir timezone local
                if requested_at.tzinfo is None:
                    requested_at = requested_at.replace(tzinfo=None)
                
                # Calcular diferencia (sin timezone para comparación)
                if requested_at.tzinfo:
                    requested_at = requested_at.replace(tzinfo=None)
                
                time_diff = now - requested_at
                
                # Si está pendiente y expirada, marcarla como expirada
                if req.get('status') == 'pending' and time_diff.total_seconds() > EXPIRATION_MINUTES * 60:
                    req['status'] = 'expired'
                    logger.info(f"Solicitud {req.get('request_id')} expirada automáticamente")
                
                valid_requests.append(req)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error al procesar fecha de solicitud {req.get('request_id')}: {e}")
                continue
        
        return valid_requests
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error al cargar solicitudes SOS: {e}")
        return []


def save_sos_request(request_data: Dict[str, Any]) -> bool:
    """
    Guarda una nueva solicitud SOS de forma segura (con bloqueo)
    Previene race conditions cuando múltiples cajas crean solicitudes simultáneamente
    """
    sos_file = _get_sos_file_path()
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(sos_file), exist_ok=True)
    
    try:
        # Leer solicitudes existentes con bloqueo
        requests_list = []
        if os.path.exists(sos_file):
            with open(sos_file, 'r+', encoding='utf-8') as f:
                _lock_file(f)
                try:
                    requests_list = json.load(f)
                    if not isinstance(requests_list, list):
                        requests_list = []
                except json.JSONDecodeError:
                    requests_list = []
                finally:
                    _unlock_file(f)
        
        # Agregar nueva solicitud
        requests_list.append(request_data)
        
        # Escribir con bloqueo
        with open(sos_file, 'w', encoding='utf-8') as f:
            _lock_file(f)
            try:
                json.dump(requests_list, f, indent=2, ensure_ascii=False)
            finally:
                _unlock_file(f)
        
        logger.info(f"✅ Solicitud SOS guardada: {request_data.get('request_id')}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar solicitud SOS: {e}")
        return False


def update_sos_request(request_id: str, updates: Dict[str, Any]) -> bool:
    """
    Actualiza una solicitud SOS existente de forma segura (con bloqueo)
    """
    sos_file = _get_sos_file_path()
    
    if not os.path.exists(sos_file):
        return False
    
    try:
        # Leer solicitudes existentes con bloqueo
        with open(sos_file, 'r+', encoding='utf-8') as f:
            _lock_file(f)
            try:
                requests_list = json.load(f)
                if not isinstance(requests_list, list):
                    return False
            except json.JSONDecodeError:
                return False
            finally:
                _unlock_file(f)
        
        # Buscar y actualizar solicitud
        found = False
        for req in requests_list:
            if req.get('request_id') == request_id:
                req.update(updates)
                found = True
                break
        
        if not found:
            return False
        
        # Escribir con bloqueo
        with open(sos_file, 'w', encoding='utf-8') as f:
            _lock_file(f)
            try:
                json.dump(requests_list, f, indent=2, ensure_ascii=False)
            finally:
                _unlock_file(f)
        
        logger.info(f"✅ Solicitud SOS actualizada: {request_id}")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar solicitud SOS: {e}")
        return False


def get_pending_requests() -> List[Dict[str, Any]]:
    """Obtiene solo las solicitudes pendientes, ordenadas por fecha (más recientes primero)"""
    all_requests = load_sos_requests()
    pending = [req for req in all_requests if req.get('status') == 'pending']
    
    # Ordenar por fecha (más recientes primero)
    pending.sort(key=lambda x: x.get('requested_at', ''), reverse=True)
    
    return pending


def can_request_drawer(employee_id: str, register_id: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica si un cajero puede hacer una solicitud
    Retorna (puede_solicitar, mensaje_error)
    """
    all_requests = load_sos_requests()
    now = datetime.now()
    
    # Verificar cooldown (última solicitud hace menos de 5 minutos)
    employee_requests = [
        req for req in all_requests
        if req.get('employee_id') == employee_id and req.get('register_id') == register_id
    ]
    
    if employee_requests:
        # Ordenar por fecha (más reciente primero)
        employee_requests.sort(key=lambda x: x.get('requested_at', ''), reverse=True)
        last_request_str = employee_requests[0].get('requested_at')
        
        if last_request_str:
            try:
                last_request = datetime.fromisoformat(last_request_str.replace('Z', '+00:00'))
                if last_request.tzinfo:
                    last_request = last_request.replace(tzinfo=None)
                
                time_diff = now - last_request
                if time_diff.total_seconds() < COOLDOWN_MINUTES * 60:
                    remaining = int((COOLDOWN_MINUTES * 60 - time_diff.total_seconds()) / 60) + 1
                    return False, f"Debes esperar {remaining} minuto(s) entre solicitudes"
            except (ValueError, TypeError):
                pass
    
    # Verificar límite diario
    today = now.strftime('%Y-%m-%d')
    today_requests = [
        req for req in employee_requests
        if req.get('requested_at', '').startswith(today)
    ]
    
    if len(today_requests) >= DAILY_LIMIT_PER_CASHIER:
        return False, f"Límite diario de {DAILY_LIMIT_PER_CASHIER} solicitudes alcanzado"
    
    return True, None

