"""
Cliente para PHP Point of Sale API
Encapsula todo el acceso a la API externa.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import requests
from flask import current_app


class PosApiClient(ABC):
    """Interfaz del cliente POS API"""
    
    @abstractmethod
    def get_sale(self, sale_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una venta por ID"""
        pass
    
    @abstractmethod
    def get_sale_items(self, sale_id: str) -> List[Dict[str, Any]]:
        """Obtiene los items de una venta"""
        pass
    
    @abstractmethod
    def get_entity_details(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene detalles de una entidad (employee, customer, register, etc.)"""
        pass
    
    @abstractmethod
    def get_employees(self, only_bartenders: bool = False) -> List[Dict[str, Any]]:
        """Obtiene lista de empleados"""
        pass
    
    @abstractmethod
    def authenticate_employee(self, username_or_pin: str, pin: Optional[str] = None, employee_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Autentica un empleado"""
        pass
    
    @abstractmethod
    def get_entradas_sales(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Obtiene ventas de entradas"""
        pass
    
    @abstractmethod
    def get_all_sales(self, limit: int = 100, max_results: int = 100, use_pagination: bool = False) -> List[Dict[str, Any]]:
        """Obtiene todas las ventas (máximo 100 items por request según PHP POS API)"""
        pass


class PhpPosApiClient(PosApiClient):
    """
    Implementación del cliente para PHP Point of Sale API.
    Encapsula pos_api.py existente.
    """
    
    def _get_api_key(self) -> Optional[str]:
        """Obtiene la API key de la configuración"""
        return current_app.config.get('API_KEY')
    
    def _get_base_url(self) -> str:
        """Obtiene la URL base de la API"""
        return current_app.config.get(
            'BASE_API_URL',
            'https://clubbb.phppointofsale.com/index.php/api/v1'
        )
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Realiza una petición GET a la API
        Returns: JSON response o None si hay error
        """
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        
        if not api_key:
            current_app.logger.error("API_KEY no configurada")
            return None
        
        url = f"{base_url}/{endpoint}"
        headers = {
            "x-api-key": api_key,
            "accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            current_app.logger.error(f"Timeout al consultar API: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error al consultar API {endpoint}: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Error inesperado al consultar API {endpoint}: {e}")
            return None
    
    def get_sale(self, sale_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una venta por ID"""
        # Normalizar sale_id (remover prefijo BMB si existe)
        numeric_id = sale_id.replace('BMB ', '').replace('BMB', '').strip()
        numeric_id = ''.join(filter(str.isdigit, numeric_id))
        
        if not numeric_id:
            return None
        
        return self._make_request(f"sales/{numeric_id}")
    
    def get_sale_items(self, sale_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene los items de una venta.
        Usa la lógica existente de pos_api.py
        """
        # Usar la función existente para mantener compatibilidad
        try:
            from ...helpers.pos_api import get_sale_items as _get_sale_items
            return _get_sale_items(sale_id)
        except Exception as e:
            current_app.logger.error(f"Error al obtener items de venta: {e}")
            return []
    
    def get_entity_details(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles de una entidad (employee, customer, register, etc.)
        Usa la lógica existente de pos_api.py
        """
        try:
            from ...helpers.pos_api import get_entity_details as _get_entity_details
            return _get_entity_details(entity_type, entity_id)
        except Exception as e:
            current_app.logger.error(f"Error al obtener detalles de entidad: {e}")
            return None
    
    def get_employees(self, only_bartenders: bool = False) -> List[Dict[str, Any]]:
        """
        Obtiene lista de empleados
        Usa la lógica existente de pos_api.py
        """
        try:
            from ...helpers.pos_api import get_employees as _get_employees
            return _get_employees(only_bartenders=only_bartenders)
        except Exception as e:
            current_app.logger.error(f"Error al obtener empleados: {e}")
            return []
    
    def authenticate_employee(self, username_or_pin: str, pin: Optional[str] = None, employee_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Autentica un empleado
        Usa la lógica existente de pos_api.py
        """
        try:
            from ...helpers.pos_api import authenticate_employee as _authenticate_employee
            return _authenticate_employee(username_or_pin, pin, employee_id)
        except Exception as e:
            current_app.logger.error(f"Error al autenticar empleado: {e}")
            return None
    
    def get_entradas_sales(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene ventas de entradas
        RESPETA límites PHP POS API: máximo 100 items por request
        Usa la lógica existente de pos_api.py
        """
        try:
            from ...helpers.pos_api import get_entradas_sales as _get_entradas_sales
            # Asegurar que limit no exceda 100 (límite PHP POS API)
            limit = min(limit, 100)
            return _get_entradas_sales(limit=limit)
        except Exception as e:
            current_app.logger.error(f"Error al obtener ventas de entradas: {e}")
            return []
    
    def get_all_sales(self, limit: int = 100, max_results: int = 100, use_pagination: bool = False) -> List[Dict[str, Any]]:
        """
        Obtiene todas las ventas
        RESPETA límites PHP POS API: máximo 100 items por request
        Usa la lógica existente de pos_api.py
        """
        try:
            from ...helpers.pos_api import get_all_sales as _get_all_sales
            # Asegurar que limit no exceda 100 (límite PHP POS API)
            limit = min(limit, 100)
            return _get_all_sales(limit=limit, max_results=max_results, use_pagination=use_pagination)
        except Exception as e:
            current_app.logger.error(f"Error al obtener todas las ventas: {e}")
            return []







