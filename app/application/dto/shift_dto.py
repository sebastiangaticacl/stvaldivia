"""
DTOs relacionados con Turnos (Shifts)
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OpenShiftRequest:
    """DTO para abrir un turno"""
    fiesta_nombre: str
    opened_by: str
    djs: Optional[str] = None
    barras_disponibles: Optional[List[str]] = None
    bartenders: Optional[List[str]] = None
    cashiers: Optional[List[str]] = None  # Cajeros que trabajarán ese día
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.fiesta_nombre or not self.fiesta_nombre.strip():
            raise ValueError("El nombre de la fiesta es requerido")
        if not self.opened_by:
            raise ValueError("opened_by es requerido")
        
        # Si no hay barras, usar las predeterminadas
        if not self.barras_disponibles:
            self.barras_disponibles = [
                'Barra Principal',
                'Barra Terraza',
                'Barra VIP',
                'Barra Exterior'
            ]
        
        # Normalizar listas vacías
        if self.bartenders is None:
            self.bartenders = []
        if self.cashiers is None:
            self.cashiers = []


@dataclass
class CloseShiftRequest:
    """DTO para cerrar un turno"""
    closed_by: str
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.closed_by:
            raise ValueError("closed_by es requerido")









