"""
Sistema de Manejo de Errores Estructurado
Excepciones de aplicación y handlers centralizados
"""
from .app_exceptions import (
    APIError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    InternalServerError,
    ServiceUnavailableError
)
from .error_handlers import register_error_handlers

__all__ = [
    'APIError',
    'ValidationError',
    'NotFoundError',
    'UnauthorizedError',
    'ForbiddenError',
    'BadRequestError',
    'InternalServerError',
    'ServiceUnavailableError',
    'register_error_handlers',
]














