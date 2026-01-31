"""
Servicio de Agente de Redes Sociales
Gestiona la generación de respuestas automáticas para redes sociales usando OpenAI.
"""
from typing import Optional, List, Dict
from datetime import datetime
import uuid

from app.application.dto.social_media_dto import (
    SocialMediaMessage,
    SocialMediaResponse,
    GenerateResponseRequest,
    GenerateResponseResponse
)
from app.infrastructure.external.openai_client import OpenAIAPIClient, OpenAIClient
from app.infrastructure.repositories.social_media_repository import (
    SocialMediaRepository,
    CsvSocialMediaRepository
)


class SocialMediaService:
    """
    Servicio que gestiona las respuestas automáticas en redes sociales.
    Usa OpenAI para generar respuestas contextualizadas.
    """
    
    # Prompt base del sistema para el agente
    DEFAULT_SYSTEM_PROMPT = """Eres BIMBA, el agente de inteligencia artificial oficial del Club BIMBA. Tu primera y principal labor es atender las redes sociales del club.

BIMBA es un espacio seguro, inclusivo y vibrante que celebra la diversidad, la música y la libertad de expresión en Valdivia, Chile.

Valores: inclusividad, diversidad, música como lenguaje universal, calidez, ambiente queer-friendly, creatividad, energía y respeto.

Tu tono debe ser: cercano, cálido, genuino, queer-friendly, entusiasta sobre la música y eventos, inclusivo, casual pero respetuoso. Responde en español chileno.

No compartas información operativa interna (ventas, métricas, etc.). Si no sabes algo, sé honesto y sugiere contactar directamente a BIMBA.

Tu función principal es responder mensajes en redes sociales de forma rápida, acogedora y que refleje los valores de BIMBA."""

    def __init__(
        self,
        openai_client: Optional[OpenAIClient] = None,
        repository: Optional[SocialMediaRepository] = None,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.7
    ):
        """
        Inicializa el servicio de redes sociales.
        
        Args:
            openai_client: Cliente de OpenAI (opcional, se crea uno por defecto)
            repository: Repositorio para historial (opcional, se crea uno por defecto)
            default_model: Modelo de OpenAI a usar por defecto
            default_temperature: Temperatura por defecto para la generación
        """
        self._openai_client = openai_client or OpenAIAPIClient()
        self._repository = repository or CsvSocialMediaRepository()
        self._default_model = default_model
        self._default_temperature = default_temperature
    
    def _get_tone_prompt_modifier(self, tone: str) -> str:
        """Obtiene un modificador del prompt según el tono deseado"""
        tone_modifiers = {
            "amigable": "Usa un tono muy amigable, cálido y cercano.",
            "profesional": "Usa un tono profesional pero accesible.",
            "casual": "Usa un tono casual y relajado.",
            "entusiasta": "Usa un tono muy entusiasta y energético.",
            "empático": "Usa un tono empático y comprensivo."
        }
        return tone_modifiers.get(tone.lower(), tone_modifiers["amigable"])
    
    def generate_response(
        self,
        request: GenerateResponseRequest
    ) -> Optional[GenerateResponseResponse]:
        """
        Genera una respuesta para un mensaje de redes sociales.
        
        Args:
            request: Request con el mensaje y contexto
            
        Returns:
            Respuesta generada o None si hay error
        """
        # Obtener historial de conversación si existe
        conversation_history = request.context
        if conversation_history is None:
            conversation_history = self._repository.get_conversation_history(
                platform=request.platform,
                sender=request.sender,
                limit=5
            )
        
        # Preparar mensajes para OpenAI
        messages = conversation_history.copy() if conversation_history else []
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Construir system prompt
        system_prompt = self.DEFAULT_SYSTEM_PROMPT
        
        # Agregar modificador de tono
        if request.tone:
            system_prompt += f"\n\n{self._get_tone_prompt_modifier(request.tone)}"
        
        # Agregar contexto de plataforma
        platform_context = {
            "instagram": "Estás respondiendo en Instagram. Mantén las respuestas concisas (idealmente menos de 200 caracteres).",
            "facebook": "Estás respondiendo en Facebook. Puedes ser un poco más detallado.",
            "twitter": "Estás respondiendo en Twitter/X. Mantén las respuestas muy concisas (máximo 280 caracteres).",
            "whatsapp": "Estás respondiendo en WhatsApp. Puedes ser más casual y usar emojis ocasionalmente.",
            "tiktok": "Estás respondiendo en TikTok. Sé creativo y enérgico."
        }
        
        if request.platform.lower() in platform_context:
            system_prompt += f"\n\n{platform_context[request.platform.lower()]}"
        
        # Calcular max_tokens según max_length
        # Aproximadamente 1 token = 4 caracteres en español
        max_tokens = min((request.max_length or 280) // 2, 500)
        
        # Generar respuesta
        response_text = self._openai_client.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            model=self._default_model,
            temperature=self._default_temperature,
            max_tokens=max_tokens
        )
        
        if not response_text:
            return None
        
        # Truncar si excede max_length
        if request.max_length and len(response_text) > request.max_length:
            response_text = response_text[:request.max_length - 3] + "..."
        
        return GenerateResponseResponse(
            response_text=response_text,
            model_used=self._default_model,
            tokens_used=None,  # Podríamos obtenerlo de la respuesta de OpenAI
            confidence=None
        )
    
    def process_message(
        self,
        message: SocialMediaMessage,
        generate_response: bool = True,
        tone: Optional[str] = None
    ) -> Optional[SocialMediaResponse]:
        """
        Procesa un mensaje recibido: lo guarda y genera una respuesta si se solicita.
        
        Args:
            message: Mensaje recibido
            generate_response: Si debe generar respuesta automáticamente
            tone: Tono para la respuesta (opcional)
            
        Returns:
            Respuesta generada o None
        """
        # Guardar mensaje
        self._repository.save_message(message)
        
        if not generate_response:
            return None
        
        # Generar respuesta
        request = GenerateResponseRequest(
            message=message.content,
            platform=message.platform,
            sender=message.sender,
            tone=tone or "amigable",
            max_length=280 if message.platform.lower() in ["twitter", "instagram"] else 500
        )
        
        response_data = self.generate_response(request)
        if not response_data:
            return None
        
        # Crear objeto de respuesta
        response = SocialMediaResponse(
            message_id=message.message_id,
            response_text=response_data.response_text,
            timestamp=datetime.now(),
            model_used=response_data.model_used,
            tokens_used=response_data.tokens_used
        )
        
        # Guardar respuesta
        self._repository.save_response(response)
        
        return response
    
    def get_conversation_history(
        self,
        platform: str,
        sender: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Obtiene el historial de conversación.
        
        Args:
            platform: Plataforma de redes sociales
            sender: Usuario (opcional)
            limit: Número máximo de mensajes
            
        Returns:
            Lista de mensajes formateados para OpenAI
        """
        return self._repository.get_conversation_history(
            platform=platform,
            sender=sender,
            limit=limit
        )









