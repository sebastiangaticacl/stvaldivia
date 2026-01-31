"""
Entidad de Dominio: Turno (Shift)
Representa un turno de trabajo en la discoteca.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ShiftStatus:
    """Estado de un turno"""
    is_open: bool
    shift_date: Optional[str] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    opened_by: Optional[str] = None
    closed_by: Optional[str] = None
    fiesta_nombre: Optional[str] = None
    djs: Optional[str] = None
    barras_disponibles: List[str] = field(default_factory=list)
    bartenders: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'is_open': self.is_open,
            'shift_date': self.shift_date,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at,
            'opened_by': self.opened_by,
            'closed_by': self.closed_by,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'barras_disponibles': self.barras_disponibles,
            'bartenders': self.bartenders
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShiftStatus':
        """Crea desde diccionario"""
        return cls(
            is_open=data.get('is_open', False),
            shift_date=data.get('shift_date'),
            opened_at=data.get('opened_at'),
            closed_at=data.get('closed_at'),
            opened_by=data.get('opened_by'),
            closed_by=data.get('closed_by'),
            fiesta_nombre=data.get('fiesta_nombre'),
            djs=data.get('djs'),
            barras_disponibles=data.get('barras_disponibles', []),
            bartenders=data.get('bartenders', [])
        )


@dataclass
class Shift:
    """
    Entidad de Dominio: Turno
    Representa un turno completo (abierto o cerrado) con toda su información.
    """
    shift_date: str
    fiesta_nombre: str
    opened_at: str
    opened_by: str
    
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    djs: Optional[str] = None
    barras_disponibles: List[str] = field(default_factory=list)
    bartenders: List[str] = field(default_factory=list)
    
    def is_open(self) -> bool:
        """Verifica si el turno está abierto"""
        return self.closed_at is None
    
    def close(self, closed_by: str, closed_at: Optional[str] = None) -> None:
        """Cierra el turno"""
        if not self.is_open():
            raise ValueError("El turno ya está cerrado")
        
        self.closed_at = closed_at or datetime.now().isoformat()
        self.closed_by = closed_by
    
    def validate_open(self) -> None:
        """Valida que el turno esté abierto"""
        if not self.is_open():
            raise ValueError("El turno no está abierto")
    
    def to_status_dict(self) -> dict:
        """Convierte a formato de status para persistencia"""
        return {
            'is_open': self.is_open(),
            'shift_date': self.shift_date,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at,
            'opened_by': self.opened_by,
            'closed_by': self.closed_by,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'barras_disponibles': self.barras_disponibles,
            'bartenders': self.bartenders
        }
    
    def to_history_dict(self) -> dict:
        """Convierte a formato para historial"""
        return {
            'shift_date': self.shift_date,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at or datetime.now().isoformat(),
            'opened_by': self.opened_by,
            'closed_by': self.closed_by,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'barras_disponibles': self.barras_disponibles,
            'bartenders': self.bartenders
        }









