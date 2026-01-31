"""
⚠️ DEPRECATED: Este módulo está deprecado y será eliminado en una versión futura.

Por favor, usa `shift_manager_compat.py` que migra gradualmente al sistema de Jornadas
basado en base de datos SQL.

Este módulo se mantiene solo para compatibilidad y como fallback.
"""
import os
import json
from datetime import datetime
from flask import current_app
import warnings

# Emitir warning de deprecación
warnings.warn(
    "shift_manager.py está deprecado. Usa shift_manager_compat.py en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

SHIFT_STATUS_FILE = 'shift_status.json'
SHIFT_HISTORY_FILE = 'shift_history.json'


def get_shift_status_file():
    """Obtiene la ruta del archivo de estado del turno"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de gestión de turnos desde archivo")
    instance_path = get_safe_instance_path() or current_app.instance_path
    os.makedirs(instance_path, exist_ok=True)
    return os.path.join(instance_path, SHIFT_STATUS_FILE)


def get_shift_status():
    """Obtiene el estado actual del turno"""
    status_file = get_shift_status_file()
    
    if not os.path.exists(status_file):
        return {
            'is_open': False,
            'shift_date': None,
            'opened_at': None,
            'closed_at': None,
            'opened_by': None
        }
    
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            status = json.load(f)
            return status
    except Exception as e:
        current_app.logger.error(f"Error al leer estado del turno: {e}")
        return {
            'is_open': False,
            'shift_date': None,
            'opened_at': None,
            'closed_at': None,
            'opened_by': None
        }


def save_shift_status(status):
    """Guarda el estado del turno"""
    status_file = get_shift_status_file()
    
    try:
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        current_app.logger.error(f"Error al guardar estado del turno: {e}")
        return False


def is_shift_open():
    """Verifica si hay un turno abierto"""
    status = get_shift_status()
    return status.get('is_open', False)


def open_shift(fiesta_nombre='', djs='', barras_disponibles=None, bartenders=None, opened_by='admin'):
    """Abre un nuevo turno con información de la fiesta"""
    status = get_shift_status()
    
    # Verificar si ya hay un turno abierto
    if status.get('is_open', False):
        return False, "Ya hay un turno abierto. Debe cerrar el turno actual antes de abrir uno nuevo."
    
    # Validar datos requeridos
    if not fiesta_nombre:
        return False, "El nombre de la fiesta es requerido"
    
    # Obtener fecha del día (formato YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now().isoformat()
    
    # Preparar listas si no son listas
    if barras_disponibles is None:
        barras_disponibles = []
    if bartenders is None:
        bartenders = []
    
    new_status = {
        'is_open': True,
        'shift_date': today,
        'opened_at': now,
        'closed_at': None,
        'opened_by': opened_by,
        'fiesta_nombre': fiesta_nombre,
        'djs': djs,
        'barras_disponibles': barras_disponibles if isinstance(barras_disponibles, list) else list(barras_disponibles),
        'bartenders': bartenders if isinstance(bartenders, list) else list(bartenders)
    }
    
    if save_shift_status(new_status):
        current_app.logger.info(f"Turno abierto el {today} a las {now} por {opened_by} - Fiesta: {fiesta_nombre}")
        return True, f"Turno abierto correctamente para el día {today}"
    else:
        return False, "Error al guardar el estado del turno"


def get_shift_history_file():
    """Obtiene la ruta del archivo de historial de turnos"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de historial de turnos desde archivo")
    instance_path = get_safe_instance_path() or current_app.instance_path
    os.makedirs(instance_path, exist_ok=True)
    return os.path.join(instance_path, SHIFT_HISTORY_FILE)


def get_shift_history():
    """Obtiene el historial de turnos cerrados"""
    history_file = get_shift_history_file()
    
    if not os.path.exists(history_file):
        return []
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            return history if isinstance(history, list) else []
    except Exception as e:
        current_app.logger.error(f"Error al leer historial de turnos: {e}")
        return []


def save_shift_to_history(shift_data):
    """Guarda un turno cerrado en el historial"""
    history_file = get_shift_history_file()
    history = get_shift_history()
    
    # Agregar el nuevo turno al inicio del historial
    history.insert(0, shift_data)
    
    # Mantener solo los últimos 365 turnos (aproximadamente 1 año)
    history = history[:365]
    
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        current_app.logger.error(f"Error al guardar historial de turnos: {e}")
        return False


def close_shift(closed_by='admin'):
    """Cierra el turno actual y lo guarda en el historial con toda la información"""
    status = get_shift_status()
    
    if not status.get('is_open', False):
        return False, "No hay un turno abierto para cerrar."
    
    closed_at = datetime.now().isoformat()
    
    # Guardar en historial antes de cerrar (con toda la información del turno)
    shift_data = {
        'shift_date': status.get('shift_date'),
        'opened_at': status.get('opened_at'),
        'closed_at': closed_at,
        'opened_by': status.get('opened_by'),
        'closed_by': closed_by,
        'fiesta_nombre': status.get('fiesta_nombre', ''),
        'djs': status.get('djs', ''),
        'barras_disponibles': status.get('barras_disponibles', []),
        'bartenders': status.get('bartenders', [])
    }
    save_shift_to_history(shift_data)
    
    # Marcar como cerrado
    status['is_open'] = False
    status['closed_at'] = closed_at
    status['closed_by'] = closed_by
    
    if save_shift_status(status):
        current_app.logger.info(f"Turno cerrado el {status.get('shift_date')} a las {closed_at} por {closed_by}")
        return True, f"Turno cerrado correctamente. Turno del día {status.get('shift_date')}"
    else:
        return False, "Error al guardar el estado del turno"

