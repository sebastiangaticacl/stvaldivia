"""
DTOs para el servicio de guardarropía.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class DepositItemRequest:
    """Request para depositar una prenda"""
    ticket_code: Optional[str] = None  # Se genera automáticamente si no se proporciona
    description: Optional[str] = None
    customer_name: str = ""  # Obligatorio
    customer_phone: str = ""  # Obligatorio
    notes: Optional[str] = None
    shift_date: Optional[str] = None
    price: float = 500.0  # Precio total (clusters * precio_unitario)
    clusters: int = 1  # Cantidad de clusters/espacios
    cluster_numbers: Optional[str] = None  # Números específicos de clusters (ej: "1,2,3")
    payment_type: str = "cash"  # Por defecto efectivo
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.customer_name or not self.customer_name.strip():
            raise ValueError("El nombre del cliente es requerido")
        
        if not self.customer_phone or not self.customer_phone.strip():
            raise ValueError("El teléfono del cliente es requerido")
        
        if self.price < 0:
            raise ValueError("El precio no puede ser negativo")
        
        if self.clusters < 1:
            raise ValueError("La cantidad de clusters debe ser al menos 1")
        
        if self.payment_type and self.payment_type not in ['cash', 'debit', 'credit', 'efectivo', 'débito', 'crédito']:
            raise ValueError("Tipo de pago inválido. Debe ser: cash, debit, credit")


@dataclass
class RetrieveItemRequest:
    """Request para retirar una prenda"""
    ticket_code: str
    retrieved_by: str
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.ticket_code or not self.ticket_code.strip():
            raise ValueError("El código de ticket es requerido")
        
        if not self.retrieved_by or not self.retrieved_by.strip():
            raise ValueError("El usuario que retira es requerido")


@dataclass
class MarkLostRequest:
    """Request para marcar un item como perdido"""
    ticket_code: str
    notes: Optional[str] = None
    
    def validate(self) -> None:
        """Valida el request"""
        if not self.ticket_code or not self.ticket_code.strip():
            raise ValueError("El código de ticket es requerido")


@dataclass
class GuardarropiaItemSummary:
    """Resumen de un item de guardarropía"""
    id: int
    ticket_code: str
    description: Optional[str]
    customer_name: Optional[str]
    status: str
    deposited_at: str
    retrieved_at: Optional[str]
    deposited_by: str
    retrieved_by: Optional[str]
    shift_date: Optional[str]
    price: Optional[float] = None
    payment_type: Optional[str] = None
    sale_id: Optional[int] = None
    notes: Optional[str] = None
    # Campos para prendas no retiradas
    photo_path: Optional[str] = None
    marked_unretrieved_at: Optional[str] = None
    marked_unretrieved_by: Optional[str] = None
    tracking_notes: Optional[str] = None
    last_tracking_date: Optional[str] = None


@dataclass
class GuardarropiaStats:
    """Estadísticas de guardarropía"""
    total_deposited: int
    total_retrieved: int
    total_lost: int
    currently_stored: int
    shift_date: Optional[str] = None
    # Estadísticas mejoradas
    total_revenue: float = 0.0  # Ingresos totales
    revenue_today: float = 0.0  # Ingresos del día/turno
    revenue_cash: float = 0.0  # Ingresos en efectivo
    revenue_debit: float = 0.0  # Ingresos en débito
    revenue_credit: float = 0.0  # Ingresos en crédito
    spaces_available: int = 90  # Espacios disponibles (90 total)
    spaces_occupied: int = 0  # Espacios ocupados
    avg_deposit_time: Optional[float] = None  # Tiempo promedio de almacenamiento (horas)
    items_today: int = 0  # Items depositados hoy
    items_retrieved_today: int = 0  # Items retirados hoy

