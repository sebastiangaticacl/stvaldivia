"""
Entidad de Dominio: Entrega (Delivery)
Representa una entrega de productos a un cliente.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Delivery:
    """
    Entidad de Dominio: Entrega
    Representa una entrega de productos registrada en el sistema.
    """
    sale_id: str
    item_name: str
    qty: int
    bartender: str
    barra: str
    timestamp: str
    admin_user: Optional[str] = None  # Usuario admin que registró desde admin/logs
    
    def validate(self) -> None:
        """Valida los datos de la entrega"""
        if not self.sale_id or not self.sale_id.strip():
            raise ValueError("sale_id es requerido")
        if not self.item_name or not self.item_name.strip():
            raise ValueError("item_name es requerido")
        if self.qty <= 0:
            raise ValueError("qty debe ser mayor a 0")
        if not self.bartender or not self.bartender.strip():
            raise ValueError("bartender es requerido")
        if not self.barra or not self.barra.strip():
            raise ValueError("barra es requerida")
    
    def to_csv_row(self) -> list:
        """Convierte a fila CSV para persistencia"""
        # Sanitizar valores
        sale_id = str(self.sale_id)[:50] if self.sale_id else ''
        item_name = str(self.item_name)[:200] if self.item_name else ''
        qty = str(self.qty) if self.qty else '0'
        bartender = str(self.bartender)[:100] if self.bartender else ''
        barra = str(self.barra)[:100] if self.barra else ''
        timestamp = self.timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return [sale_id, item_name, qty, bartender, barra, timestamp]
    
    @classmethod
    def from_csv_row(cls, row: list) -> 'Delivery':
        """Crea desde fila CSV"""
        if len(row) < 6:
            raise ValueError(f"Fila CSV inválida: {row}")
        
        return cls(
            sale_id=row[0] or '',
            item_name=row[1] or '',
            qty=int(row[2] or 0),
            bartender=row[3] or '',
            barra=row[4] or '',
            timestamp=row[5] or ''
        )
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'sale_id': self.sale_id,
            'item_name': self.item_name,
            'qty': self.qty,
            'bartender': self.bartender,
            'barra': self.barra,
            'timestamp': self.timestamp
        }









