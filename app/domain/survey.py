"""
Entidades de Dominio: Encuestas
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List


@dataclass
class SurveyResponse:
    """
    Entidad: Respuesta de Encuesta
    Representa una respuesta de un cliente a la encuesta.
    """
    barra: str  # '1' o '2'
    rating: int  # 1-5
    timestamp: str
    comment: str = ''
    fiesta_nombre: str = ''
    djs: str = ''
    bartender_nombre: str = ''
    fecha_sesion: str = ''
    
    def validate(self) -> None:
        """Valida los datos de la respuesta"""
        if self.barra not in ['1', '2']:
            raise ValueError("barra debe ser '1' o '2'")
        if not (1 <= self.rating <= 5):
            raise ValueError("rating debe estar entre 1 y 5")
        if not self.fecha_sesion:
            # Calcular fecha de sesión si no está
            now = datetime.now()
            if now.hour < 4 or (now.hour == 4 and now.minute < 30):
                self.fecha_sesion = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                self.fecha_sesion = now.strftime('%Y-%m-%d')
    
    def to_csv_row(self) -> list:
        """Convierte a fila CSV"""
        return [
            self.timestamp,
            self.barra,
            str(self.rating),
            self.comment or '',
            self.fiesta_nombre or '',
            self.djs or '',
            self.bartender_nombre or '',
            self.fecha_sesion
        ]


@dataclass
class SurveySession:
    """
    Entidad: Sesión de Encuesta
    Representa una sesión de encuestas asociada a un turno.
    """
    fecha_sesion: str
    fiesta_nombre: str
    hora_inicio: str
    estado: str = 'abierta'  # 'abierta' o 'cerrada'
    
    djs: str = ''
    bartenders: str = ''  # Separados por coma
    hora_fin: str = ''
    total_respuestas: int = 0
    promedio_rating: float = 0.0
    
    def close(self, hora_fin: Optional[str] = None) -> None:
        """Cierra la sesión"""
        if self.estado == 'cerrada':
            raise ValueError("La sesión ya está cerrada")
        
        self.estado = 'cerrada'
        self.hora_fin = hora_fin or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

