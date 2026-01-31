"""
DTOs relacionados con Encuestas (Surveys)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SurveyResponseRequest:
    """DTO para guardar una respuesta de encuesta"""
    barra: str  # '1' o '2'
    rating: int  # 1-5
    comment: Optional[str] = None
    bartender_nombre: Optional[str] = None
    
    # Estos se pueden obtener del turno activo si no se proporcionan
    fiesta_nombre: Optional[str] = None
    djs: Optional[str] = None
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if self.barra not in ['1', '2']:
            raise ValueError("barra debe ser '1' o '2'")
        if not (1 <= self.rating <= 5):
            raise ValueError("rating debe estar entre 1 y 5")









