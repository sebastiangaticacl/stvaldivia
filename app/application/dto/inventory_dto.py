"""
DTOs para el servicio de inventario.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class RegisterInitialInventoryRequest:
    """Request para registrar inventario inicial"""
    barra: str
    items: Dict[str, int]  # {product_name: initial_quantity}
    registered_by: str
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.barra:
            raise ValueError("El nombre de la barra es requerido")
        if not self.items:
            raise ValueError("Debe haber al menos un item en el inventario")
        if not self.registered_by:
            raise ValueError("El usuario que registra es requerido")
        
        # Validar que las cantidades sean positivas
        for product_name, quantity in self.items.items():
            if not product_name or not product_name.strip():
                raise ValueError("El nombre del producto no puede estar vacío")
            if quantity < 0:
                raise ValueError(f"La cantidad de {product_name} no puede ser negativa")


@dataclass
class FinalizeInventoryRequest:
    """Request para finalizar inventario"""
    barra: str
    actual_quantities: Optional[Dict[str, int]] = None  # {product_name: actual_quantity}
    finalized_by: str = ""
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.barra:
            raise ValueError("El nombre de la barra es requerido")
        if not self.finalized_by:
            raise ValueError("El usuario que finaliza es requerido")


@dataclass
class InventorySummary:
    """Resumen de inventario"""
    barra: str
    shift_date: str
    total_items: int
    total_initial: int
    total_delivered: int
    total_expected_final: int
    total_actual_final: Optional[int] = None
    total_difference: Optional[int] = None
    is_finalized: bool = False
    items: List[Dict] = None









