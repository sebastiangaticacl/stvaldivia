"""
DTOs relacionados con Entregas (Deliveries)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanSaleRequest:
    """DTO para escanear una venta"""
    sale_id: str  # Puede tener prefijo "BMB " o no
    
    def normalize_sale_id(self) -> str:
        """Normaliza el ID de venta, removiendo prefijo si existe"""
        sale_id = self.sale_id.strip()
        # Remover prefijo "BMB " o "BMB"
        if sale_id.startswith("BMB "):
            return sale_id[4:].strip()
        elif sale_id.startswith("BMB"):
            return sale_id[3:].strip()
        return sale_id
    
    def get_numeric_id(self) -> str:
        """Obtiene solo el ID numérico"""
        normalized = self.normalize_sale_id()
        # Remover cualquier caracter no numérico
        return ''.join(filter(str.isdigit, normalized))
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.sale_id or not self.sale_id.strip():
            raise ValueError("sale_id es requerido")


@dataclass
class DeliveryRequest:
    """DTO para registrar una entrega"""
    sale_id: str
    item_name: str
    qty: int
    bartender: str
    barra: str
    admin_user: Optional[str] = None  # Usuario admin que registró desde admin/logs
    
    def validate(self) -> None:
        """Valida los datos del request"""
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









