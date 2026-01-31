"""
Cliente para OpenAI API
Encapsula todo el acceso a la API de OpenAI para el agente de redes sociales.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from flask import current_app
import openai


class OpenAIClient(ABC):
    """Interfaz del cliente OpenAI"""
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """Genera una respuesta usando OpenAI"""
        pass


class OpenAIAPIClient(OpenAIClient):
    """
    Implementación del cliente para OpenAI API.
    Usa la biblioteca oficial de OpenAI.
    """
    
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None, project: Optional[str] = None):
        """
        Inicializa el cliente de OpenAI.
        
        Args:
            api_key: API key de OpenAI (opcional, se puede obtener de config)
            organization: Organization ID de OpenAI (opcional)
            project: Project ID de OpenAI (opcional, requerido para Admin Keys)
        """
        self._api_key = api_key
        self._organization = organization
        self._project = project
        self._client = None
    
    def _get_api_key(self) -> Optional[str]:
        """Obtiene la API key de la configuración"""
        if self._api_key:
            return self._api_key
        
        try:
            return current_app.config.get('OPENAI_API_KEY')
        except RuntimeError:
            # Si no hay contexto de Flask, usar variable de entorno
            import os
            return os.environ.get('OPENAI_API_KEY')
    
    def _get_organization(self) -> Optional[str]:
        """Obtiene la organization ID de la configuración"""
        if self._organization:
            return self._organization
        
        try:
            return current_app.config.get('OPENAI_ORGANIZATION_ID')
        except RuntimeError:
            import os
            return os.environ.get('OPENAI_ORGANIZATION_ID')
    
    def _get_project(self) -> Optional[str]:
        """Obtiene el Project ID de la configuración"""
        if self._project:
            return self._project
        
        try:
            return current_app.config.get('OPENAI_PROJECT_ID')
        except RuntimeError:
            import os
            return os.environ.get('OPENAI_PROJECT_ID')
    
    def _get_client(self) -> Optional[openai.OpenAI]:
        """Obtiene o crea el cliente de OpenAI"""
        if self._client:
            return self._client
        
        api_key = self._get_api_key()
        if not api_key:
            try:
                current_app.logger.error("OPENAI_API_KEY no configurada")
            except RuntimeError:
                import logging
                logging.error("OPENAI_API_KEY no configurada")
            return None
        
        try:
            client_kwargs = {"api_key": api_key}
            organization = self._get_organization()
            if organization:
                client_kwargs["organization"] = organization
            
            project = self._get_project()
            if project:
                client_kwargs["project"] = project
            
            # Agregar timeout para evitar conexiones colgadas (6 segundos)
            client_kwargs["timeout"] = 6.0
            
            self._client = openai.OpenAI(**client_kwargs)
            return self._client
        except Exception as e:
            try:
                current_app.logger.error(f"Error al inicializar cliente de OpenAI: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error al inicializar cliente de OpenAI: {e}")
            return None
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Genera una respuesta usando OpenAI.
        
        Args:
            messages: Lista de mensajes en formato [{"role": "user", "content": "..."}]
            system_prompt: Prompt del sistema (opcional)
            model: Modelo a usar (default: gpt-4o-mini)
            temperature: Temperatura para la generación (0-1)
            max_tokens: Máximo de tokens en la respuesta
            
        Returns:
            Respuesta generada o None si hay error
        """
        client = self._get_client()
        if not client:
            return None
        
        # Preparar mensajes
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.extend(messages)
        
        try:
            # Timeout de 5 segundos para la llamada - si no responde rápido, fallback
            response = client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=5.0
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            
            return None
        except openai.AuthenticationError as e:
            try:
                current_app.logger.error(f"Error de autenticación en OpenAI: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error de autenticación en OpenAI: {e}")
            return None
        except openai.RateLimitError as e:
            try:
                current_app.logger.error(f"Rate limit excedido en OpenAI: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Rate limit excedido en OpenAI: {e}")
            return None
        except openai.APIError as e:
            try:
                current_app.logger.error(f"Error en API de OpenAI: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error en API de OpenAI: {e}")
            return None
        except Exception as e:
            try:
                current_app.logger.error(f"Error inesperado al generar respuesta: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error inesperado al generar respuesta: {e}")
            return None

