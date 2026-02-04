"""
Cliente Dialogflow: deshabilitado (ya no usamos Google Cloud).

Se mantiene la interfaz para compatibilidad. Todas las llamadas retornan None
y el resto de la app usa OpenAI o fallbacks.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class DialogflowClient(ABC):
    """Interfaz del cliente Dialogflow (compatibilidad)."""

    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        pass


class DialogflowAPIClient(DialogflowClient):
    """
    Stub: Dialogflow ya no se usa. Retorna None para que los callers
    usen OpenAI o respuestas por reglas.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        language_code: str = "es",
    ):
        pass

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        session_id: str = "default",
    ) -> Optional[str]:
        return None

    def detect_intent(
        self,
        text: str,
        session_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        return None
