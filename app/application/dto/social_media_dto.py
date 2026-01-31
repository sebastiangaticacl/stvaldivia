"""
DTOs para el servicio de redes sociales.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class SocialMediaMessage:
    """Representa un mensaje de redes sociales"""
    message_id: str
    platform: str  # "instagram", "facebook", "twitter", "whatsapp", etc.
    sender: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None  # URLs, imágenes, etc.


@dataclass
class SocialMediaResponse:
    """Representa una respuesta generada para redes sociales"""
    message_id: str
    response_text: str
    timestamp: datetime
    model_used: str
    tokens_used: Optional[int] = None
    metadata: Optional[Dict] = None


@dataclass
class GenerateResponseRequest:
    """Request para generar una respuesta"""
    message: str
    platform: str
    sender: Optional[str] = None
    context: Optional[List[Dict[str, str]]] = None  # Historial de conversación
    tone: Optional[str] = "amigable"  # "amigable", "profesional", "casual", etc.
    max_length: Optional[int] = 280  # Longitud máxima de la respuesta


@dataclass
class GenerateResponseResponse:
    """Response con la respuesta generada"""
    response_text: str
    model_used: str
    tokens_used: Optional[int] = None
    confidence: Optional[float] = None









