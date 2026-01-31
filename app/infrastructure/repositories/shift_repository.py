"""
Repositorio de Turnos (Shifts)
Interfaz e implementación JSON.
"""
from abc import ABC, abstractmethod
import os
import json
from typing import Optional, List
from flask import current_app

from app.domain.shift import Shift, ShiftStatus


class ShiftRepository(ABC):
    """Interfaz del repositorio de turnos"""
    
    @abstractmethod
    def get_current_shift_status(self) -> ShiftStatus:
        """Obtiene el estado actual del turno"""
        pass
    
    @abstractmethod
    def save_shift_status(self, status: ShiftStatus) -> bool:
        """Guarda el estado del turno"""
        pass
    
    @abstractmethod
    def save_to_history(self, shift: Shift) -> bool:
        """Guarda un turno en el historial"""
        pass
    
    @abstractmethod
    def get_shift_history(self, limit: int = 30) -> List[dict]:
        """Obtiene el historial de turnos cerrados"""
        pass


class JsonShiftRepository(ShiftRepository):
    """
    Implementación del repositorio usando archivos JSON.
    Mantiene compatibilidad con shift_manager.py existente.
    """
    
    STATUS_FILE = 'shift_status.json'
    HISTORY_FILE = 'shift_history.json'
    HISTORY_LIMIT = 365  # Mantener últimos 365 turnos
    
    def _get_status_file_path(self) -> str:
        """Obtiene la ruta del archivo de estado"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de estado de turnos desde archivo")
        instance_path = get_safe_instance_path() or current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.STATUS_FILE)
    
    def _get_history_file_path(self) -> str:
        """Obtiene la ruta del archivo de historial"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de historial de turnos desde archivo")
        instance_path = get_safe_instance_path() or current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.HISTORY_FILE)
    
    def get_current_shift_status(self) -> ShiftStatus:
        """Obtiene el estado actual del turno"""
        status_file = self._get_status_file_path()
        
        if not os.path.exists(status_file):
            return ShiftStatus(is_open=False)
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ShiftStatus.from_dict(data)
        except Exception as e:
            current_app.logger.error(f"Error al leer estado del turno: {e}")
            return ShiftStatus(is_open=False)
    
    def save_shift_status(self, status: ShiftStatus) -> bool:
        """Guarda el estado del turno"""
        status_file = self._get_status_file_path()
        
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar estado del turno: {e}")
            return False
    
    def save_to_history(self, shift: Shift) -> bool:
        """Guarda un turno cerrado en el historial"""
        history_file = self._get_history_file_path()
        history = self.get_shift_history(limit=9999)  # Obtener todo el historial
        
        # Agregar el nuevo turno al inicio
        shift_dict = shift.to_history_dict()
        history.insert(0, shift_dict)
        
        # Mantener solo los últimos N turnos
        history = history[:self.HISTORY_LIMIT]
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar historial de turnos: {e}")
            return False
    
    def get_shift_history(self, limit: int = 30) -> List[dict]:
        """Obtiene el historial de turnos cerrados"""
        history_file = self._get_history_file_path()
        
        if not os.path.exists(history_file):
            return []
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                if isinstance(history, list):
                    return history[:limit]
                return []
        except Exception as e:
            current_app.logger.error(f"Error al leer historial de turnos: {e}")
            return []









