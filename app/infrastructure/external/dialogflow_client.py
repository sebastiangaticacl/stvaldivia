"""
Cliente para Google Dialogflow API
Encapsula todo el acceso a la API de Dialogflow para el agente de redes sociales.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from flask import current_app
import os
import json


class DialogflowClient(ABC):
    """Interfaz del cliente Dialogflow"""
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """Genera una respuesta usando Dialogflow"""
        pass


class DialogflowAPIClient(DialogflowClient):
    """
    Implementación del cliente para Dialogflow API.
    Usa la biblioteca oficial de Google Cloud Dialogflow.
    """
    
    def __init__(
        self, 
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        language_code: str = "es"
    ):
        """
        Inicializa el cliente de Dialogflow.
        
        Args:
            project_id: ID del proyecto de Google Cloud (opcional, se puede obtener de config)
            credentials_path: Ruta al archivo JSON de credenciales (opcional)
            language_code: Código de idioma (default: "es" para español)
        """
        self._project_id = project_id
        self._credentials_path = credentials_path
        self._language_code = language_code
        self._client = None
        self._session_client = None
    
    def _get_project_id(self) -> Optional[str]:
        """Obtiene el Project ID de la configuración"""
        if self._project_id:
            return self._project_id
        
        try:
            return current_app.config.get('DIALOGFLOW_PROJECT_ID')
        except RuntimeError:
            return os.environ.get('DIALOGFLOW_PROJECT_ID')
    
    def _get_credentials_path(self) -> Optional[str]:
        """Obtiene la ruta a las credenciales de la configuración"""
        if self._credentials_path:
            return self._credentials_path
        
        try:
            return current_app.config.get('DIALOGFLOW_CREDENTIALS_PATH')
        except RuntimeError:
            return os.environ.get('DIALOGFLOW_CREDENTIALS_PATH') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    def _get_language_code(self) -> str:
        """Obtiene el código de idioma"""
        try:
            return current_app.config.get('DIALOGFLOW_LANGUAGE_CODE', self._language_code)
        except RuntimeError:
            return os.environ.get('DIALOGFLOW_LANGUAGE_CODE', self._language_code)
    
    def _get_client(self):
        """Obtiene o crea el cliente de Dialogflow"""
        if self._client:
            return self._client
        
        project_id = self._get_project_id()
        if not project_id:
            try:
                current_app.logger.error("DIALOGFLOW_PROJECT_ID no configurado")
            except RuntimeError:
                import logging
                logging.error("DIALOGFLOW_PROJECT_ID no configurado")
            return None
        
        try:
            from google.cloud import dialogflow
            
            # Configurar credenciales si están disponibles
            credentials_path = self._get_credentials_path()
            if credentials_path and os.path.exists(credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
            # Crear cliente de sesiones
            self._session_client = dialogflow.SessionsClient()
            self._client = dialogflow
            
            return self._client
        except ImportError:
            try:
                current_app.logger.error("google-cloud-dialogflow no está instalado. Ejecuta: pip install google-cloud-dialogflow")
            except RuntimeError:
                import logging
                logging.error("google-cloud-dialogflow no está instalado")
            return None
        except Exception as e:
            try:
                current_app.logger.error(f"Error al inicializar cliente de Dialogflow: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error al inicializar cliente de Dialogflow: {e}")
            return None
    
    def _get_session_path(self, session_id: str = "default") -> Optional[str]:
        """Obtiene la ruta de la sesión"""
        project_id = self._get_project_id()
        if not project_id or not self._session_client:
            return None
        
        return self._session_client.session_path(project_id, session_id)
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        session_id: str = "default"
    ) -> Optional[str]:
        """
        Genera una respuesta usando Dialogflow.
        
        Args:
            messages: Lista de mensajes en formato [{"role": "user", "content": "..."}]
            system_prompt: Prompt del sistema (opcional, se puede usar como contexto)
            model: Modelo a usar (ignorado en Dialogflow, usa el agente configurado)
            temperature: Temperatura para la generación (ignorado en Dialogflow)
            max_tokens: Máximo de tokens (ignorado en Dialogflow)
            session_id: ID de sesión para mantener contexto (default: "default")
            
        Returns:
            Respuesta generada o None si hay error
        """
        client = self._get_client()
        if not client or not self._session_client:
            return None
        
        # Obtener el último mensaje del usuario
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return None
        
        try:
            from google.cloud.dialogflow import TextInput, QueryInput
            
            session_path = self._get_session_path(session_id)
            if not session_path:
                return None
            
            # Crear entrada de texto
            text_input = TextInput(text=user_message, language_code=self._get_language_code())
            query_input = QueryInput(text=text_input)
            
            # Enviar consulta a Dialogflow
            response = self._session_client.detect_intent(
                request={"session": session_path, "query_input": query_input}
            )
            
            # Obtener respuesta
            if response.query_result:
                fulfillment_text = response.query_result.fulfillment_text
                if fulfillment_text:
                    return fulfillment_text.strip()
                
                # Si no hay texto de cumplimiento, usar el texto alternativo
                if response.query_result.alternative_query_results:
                    for alt_result in response.query_result.alternative_query_results:
                        if alt_result.fulfillment_text:
                            return alt_result.fulfillment_text.strip()
            
            return None
            
        except Exception as e:
            try:
                current_app.logger.error(f"Error al generar respuesta con Dialogflow: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error al generar respuesta con Dialogflow: {e}")
            return None
    
    def detect_intent(
        self,
        text: str,
        session_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta la intención del usuario usando Dialogflow.
        
        Args:
            text: Texto del usuario
            session_id: ID de sesión
            
        Returns:
            Diccionario con información de la intención o None si hay error
        """
        client = self._get_client()
        if not client or not self._session_client:
            return None
        
        try:
            from google.cloud.dialogflow import TextInput, QueryInput
            
            session_path = self._get_session_path(session_id)
            if not session_path:
                return None
            
            text_input = TextInput(text=text, language_code=self._get_language_code())
            query_input = QueryInput(text=text_input)
            
            response = self._session_client.detect_intent(
                request={"session": session_path, "query_input": query_input}
            )
            
            if response.query_result:
                return {
                    "intent": response.query_result.intent.display_name if response.query_result.intent else None,
                    "confidence": response.query_result.intent_detection_confidence,
                    "fulfillment_text": response.query_result.fulfillment_text,
                    "parameters": dict(response.query_result.parameters) if response.query_result.parameters else {}
                }
            
            return None
            
        except Exception as e:
            try:
                current_app.logger.error(f"Error al detectar intención con Dialogflow: {e}")
            except RuntimeError:
                import logging
                logging.error(f"Error al detectar intención con Dialogflow: {e}")
            return None

