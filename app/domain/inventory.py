"""
Entidad de Dominio: Inventario
Representa el inventario de botellas por barra en un turno.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict


@dataclass
class InventoryItem:
    """
    Representa un item de inventario (botella/producto) en una barra.
    """
    product_name: str
    initial_quantity: int
    delivered_quantity: int = 0
    final_quantity: Optional[int] = None  # Calculado al cerrar
    
    def calculate_final(self) -> int:
        """Calcula la cantidad final esperada"""
        return self.initial_quantity - self.delivered_quantity
    
    def set_final_quantity(self, actual_quantity: Optional[int] = None) -> None:
        """
        Establece la cantidad final.
        Si no se proporciona, calcula automáticamente.
        """
        if actual_quantity is not None:
            self.final_quantity = actual_quantity
        else:
            self.final_quantity = self.calculate_final()
    
    def get_difference(self) -> int:
        """
        Calcula la diferencia entre lo esperado y lo real.
        Retorna negativo si hay faltante, positivo si hay sobrante.
        """
        if self.final_quantity is None:
            return 0
        return self.final_quantity - self.calculate_final()
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'product_name': self.product_name,
            'initial_quantity': self.initial_quantity,
            'delivered_quantity': self.delivered_quantity,
            'final_quantity': self.final_quantity,
            'expected_final': self.calculate_final(),
            'difference': self.get_difference()
        }


@dataclass
class BarInventory:
    """
    Inventario completo de una barra en un turno.
    """
    barra: str
    shift_date: str
    items: Dict[str, InventoryItem] = field(default_factory=dict)
    registered_at: Optional[str] = None
    registered_by: Optional[str] = None
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None
    
    def add_item(self, product_name: str, initial_quantity: int) -> None:
        """Agrega o actualiza un item de inventario"""
        if product_name in self.items:
            self.items[product_name].initial_quantity = initial_quantity
        else:
            self.items[product_name] = InventoryItem(
                product_name=product_name,
                initial_quantity=initial_quantity
            )
    
    def record_delivery(self, product_name: str, quantity: int) -> None:
        """Registra una entrega de producto"""
        if product_name in self.items:
            self.items[product_name].delivered_quantity += quantity
        else:
            # Si no existe, crear con cantidad inicial 0
            self.items[product_name] = InventoryItem(
                product_name=product_name,
                initial_quantity=0,
                delivered_quantity=quantity
            )
    
    def finalize(self, finalized_by: str, actual_quantities: Optional[Dict[str, int]] = None) -> None:
        """
        Finaliza el inventario calculando cantidades finales.
        
        Args:
            finalized_by: Usuario que finaliza
            actual_quantities: Cantidades reales contadas (opcional)
        """
        self.finalized_at = datetime.now().isoformat()
        self.finalized_by = finalized_by
        
        for product_name, item in self.items.items():
            actual_qty = actual_quantities.get(product_name) if actual_quantities else None
            item.set_final_quantity(actual_qty)
    
    def get_summary(self) -> Dict[str, any]:
        """Obtiene un resumen del inventario"""
        total_initial = sum(item.initial_quantity for item in self.items.values())
        total_delivered = sum(item.delivered_quantity for item in self.items.values())
        total_expected_final = sum(item.calculate_final() for item in self.items.values())
        total_actual_final = sum(
            item.final_quantity or item.calculate_final() 
            for item in self.items.values()
        )
        total_difference = total_actual_final - total_expected_final
        
        return {
            'barra': self.barra,
            'shift_date': self.shift_date,
            'total_items': len(self.items),
            'total_initial': total_initial,
            'total_delivered': total_delivered,
            'total_expected_final': total_expected_final,
            'total_actual_final': total_actual_final,
            'total_difference': total_difference,
            'is_finalized': self.finalized_at is not None
        }
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'barra': self.barra,
            'shift_date': self.shift_date,
            'items': {name: item.to_dict() for name, item in self.items.items()},
            'registered_at': self.registered_at,
            'registered_by': self.registered_by,
            'finalized_at': self.finalized_at,
            'finalized_by': self.finalized_by,
            'summary': self.get_summary()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BarInventory':
        """Crea desde diccionario"""
        inventory = cls(
            barra=data['barra'],
            shift_date=data['shift_date'],
            registered_at=data.get('registered_at'),
            registered_by=data.get('registered_by'),
            finalized_at=data.get('finalized_at'),
            finalized_by=data.get('finalized_by')
        )
        
        # Cargar items
        items_data = data.get('items', {})
        for product_name, item_data in items_data.items():
            inventory.items[product_name] = InventoryItem(
                product_name=item_data['product_name'],
                initial_quantity=item_data['initial_quantity'],
                delivered_quantity=item_data.get('delivered_quantity', 0),
                final_quantity=item_data.get('final_quantity')
            )
        
        return inventory


@dataclass
class ShiftInventory:
    """
    Inventario completo de un turno (todas las barras).
    """
    shift_date: str
    barras: Dict[str, BarInventory] = field(default_factory=dict)
    
    def get_bar_inventory(self, barra: str) -> BarInventory:
        """Obtiene o crea el inventario de una barra"""
        if barra not in self.barras:
            self.barras[barra] = BarInventory(
                barra=barra,
                shift_date=self.shift_date
            )
        return self.barras[barra]
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'shift_date': self.shift_date,
            'barras': {barra: inv.to_dict() for barra, inv in self.barras.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShiftInventory':
        """Crea desde diccionario"""
        shift_inv = cls(shift_date=data['shift_date'])
        
        barras_data = data.get('barras', {})
        for barra, bar_data in barras_data.items():
            shift_inv.barras[barra] = BarInventory.from_dict(bar_data)
        
        return shift_inv









