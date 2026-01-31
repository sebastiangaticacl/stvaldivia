"""
Excepciones de Aplicación
Clases de error estructuradas para toda la aplicación
"""
from typing import Optional, Dict, Any
from flask import Response
import json


class APIError(Exception):
    """
    Excepción base para errores de la API.
    
    Todas las excepciones de aplicación deben heredar de esta clase.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        """
        Inicializa un error de API.
        
        Args:
            message: Mensaje técnico del error (para logging)
            status_code: Código HTTP de estado
            error_code: Código de error único (para el cliente)
            details: Detalles adicionales del error
            user_message: Mensaje amigable para mostrar al usuario
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.user_message = user_message or message
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el error a diccionario para respuesta JSON.
        
        Returns:
            dict: Diccionario con información del error
        """
        return {
            'error': self.user_message,
            'code': self.error_code,
            'status_code': self.status_code,
            'details': self.details if self.details else None
        }
    
    def to_response(self) -> Response:
        """
        Convierte el error a respuesta Flask.
        
        Returns:
            Response: Respuesta HTTP con el error
        """
        from flask import jsonify
        response = jsonify(self.to_dict())
        response.status_code = self.status_code
        return response


class ValidationError(APIError):
    """Error de validación de datos"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        user_message: Optional[str] = None
    ):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        
        super().__init__(
            message=message,
            status_code=400,
            error_code='VALIDATION_ERROR',
            details=details,
            user_message=user_message or f"Error de validación: {message}"
        )


class BadRequestError(APIError):
    """Error 400: Solicitud incorrecta"""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code='BAD_REQUEST',
            user_message=user_message or message
        )


class UnauthorizedError(APIError):
    """Error 401: No autorizado"""
    
    def __init__(self, message: str = "No autorizado", user_message: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code='UNAUTHORIZED',
            user_message=user_message or "No tienes autorización para realizar esta acción"
        )


class ForbiddenError(APIError):
    """Error 403: Prohibido"""
    
    def __init__(self, message: str = "Acceso prohibido", user_message: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code='FORBIDDEN',
            user_message=user_message or "No tienes permiso para acceder a este recurso"
        )


class NotFoundError(APIError):
    """Error 404: Recurso no encontrado"""
    
    def __init__(self, resource: str = "Recurso", user_message: Optional[str] = None):
        message = f"{resource} no encontrado"
        super().__init__(
            message=message,
            status_code=404,
            error_code='NOT_FOUND',
            user_message=user_message or message
        )


class InternalServerError(APIError):
    """Error 500: Error interno del servidor"""
    
    def __init__(self, message: str = "Error interno del servidor", user_message: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code='INTERNAL_ERROR',
            user_message=user_message or "Ocurrió un error inesperado. Por favor, intenta nuevamente."
        )


class ServiceUnavailableError(APIError):
    """Error 503: Servicio no disponible"""
    
    def __init__(self, service: str = "Servicio", user_message: Optional[str] = None):
        message = f"{service} no está disponible"
        super().__init__(
            message=message,
            status_code=503,
            error_code='SERVICE_UNAVAILABLE',
            user_message=user_message or f"El {service.lower()} no está disponible en este momento. Por favor, intenta más tarde."
        )


class RateLimitError(APIError):
    """Error 429: Rate limit excedido"""
    
    def __init__(self, retry_after: Optional[int] = None, user_message: Optional[str] = None):
        message = "Rate limit excedido"
        details = {}
        if retry_after:
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details=details,
            user_message=user_message or "Has realizado demasiadas solicitudes. Por favor, espera un momento."
        )














