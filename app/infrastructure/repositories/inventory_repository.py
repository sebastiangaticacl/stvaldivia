"""
Repositorio de Inventario
Interfaz e implementación JSON.
"""
from abc import ABC, abstractmethod
import os
import json
from typing import Optional, Dict, List
from flask import current_app

from app.domain.inventory import ShiftInventory, BarInventory


class InventoryRepository(ABC):
    """Interfaz del repositorio de inventario"""
    
    @abstractmethod
    def save_shift_inventory(self, inventory: ShiftInventory) -> bool:
        """Guarda el inventario de un turno"""
        pass
    
    @abstractmethod
    def get_shift_inventory(self, shift_date: str) -> Optional[ShiftInventory]:
        """Obtiene el inventario de un turno"""
        pass
    
    @abstractmethod
    def get_current_shift_inventory(self) -> Optional[ShiftInventory]:
        """Obtiene el inventario del turno actual"""
        pass
    
    @abstractmethod
    def get_bar_inventory(self, shift_date: str, barra: str) -> Optional[BarInventory]:
        """Obtiene el inventario de una barra específica"""
        pass
    
    @abstractmethod
    def record_delivery(self, barra: str, product_name: str, quantity: int) -> bool:
        """Registra una entrega de producto (descuenta del inventario)"""
        pass


class JsonInventoryRepository(InventoryRepository):
    """
    Implementación del repositorio usando archivos JSON.
    Almacena inventario por fecha de turno.
    """
    
    INVENTORY_FILE = 'inventory.json'
    
    def _get_inventory_file_path(self) -> str:
        """Obtiene la ruta del archivo de inventario"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de inventario desde archivo")
        instance_path = get_safe_instance_path()
        if not instance_path:
            instance_path = os.path.join(os.getcwd(), 'instance')
        
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.INVENTORY_FILE)
    
    def _load_all_inventories(self) -> Dict[str, dict]:
        """Carga todos los inventarios desde el archivo"""
        file_path = self._get_inventory_file_path()
        
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            current_app.logger.error(f"Error al cargar inventario: {e}")
            return {}
    
    def _save_all_inventories(self, inventories: Dict[str, dict]) -> bool:
        """Guarda todos los inventarios en el archivo"""
        file_path = self._get_inventory_file_path()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(inventories, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            current_app.logger.error(f"Error al guardar inventario: {e}")
            return False
    
    def save_shift_inventory(self, inventory: ShiftInventory) -> bool:
        """Guarda el inventario de un turno"""
        try:
            all_inventories = self._load_all_inventories()
            all_inventories[inventory.shift_date] = inventory.to_dict()
            return self._save_all_inventories(all_inventories)
        except Exception as e:
            current_app.logger.error(f"Error al guardar inventario del turno: {e}")
            return False
    
    def get_shift_inventory(self, shift_date: str) -> Optional[ShiftInventory]:
        """Obtiene el inventario de un turno"""
        try:
            all_inventories = self._load_all_inventories()
            inventory_data = all_inventories.get(shift_date)
            
            if not inventory_data:
                return None
            
            return ShiftInventory.from_dict(inventory_data)
        except Exception as e:
            current_app.logger.error(f"Error al obtener inventario del turno: {e}")
            return None
    
    def get_current_shift_inventory(self) -> Optional[ShiftInventory]:
        """Obtiene el inventario del turno actual"""
        try:
            from app.infrastructure.repositories.shift_repository import JsonShiftRepository
            shift_repo = JsonShiftRepository()
            shift_status = shift_repo.get_current_shift_status()
            
            if not shift_status.is_open or not shift_status.shift_date:
                return None
            
            return self.get_shift_inventory(shift_status.shift_date)
        except Exception as e:
            current_app.logger.error(f"Error al obtener inventario del turno actual: {e}")
            return None
    
    def get_bar_inventory(self, shift_date: str, barra: str) -> Optional[BarInventory]:
        """Obtiene el inventario de una barra específica"""
        try:
            shift_inventory = self.get_shift_inventory(shift_date)
            if not shift_inventory:
                return None
            
            return shift_inventory.barras.get(barra)
        except Exception as e:
            current_app.logger.error(f"Error al obtener inventario de barra: {e}")
            return None
    
    def record_delivery(self, barra: str, product_name: str, quantity: int) -> bool:
        """
        Registra una entrega de producto (descuenta del inventario).
        Busca en el turno actual.
        """
        try:
            shift_inventory = self.get_current_shift_inventory()
            if not shift_inventory:
                # Si no hay inventario del turno actual, no hacer nada
                return True
            
            bar_inventory = shift_inventory.get_bar_inventory(barra)
            bar_inventory.record_delivery(product_name, quantity)
            
            return self.save_shift_inventory(shift_inventory)
        except Exception as e:
            current_app.logger.error(f"Error al registrar entrega en inventario: {e}")
            return False









