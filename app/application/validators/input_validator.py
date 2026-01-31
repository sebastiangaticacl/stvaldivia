"""
Validador Genérico de Entrada
Validaciones comunes para inputs del usuario
"""
import re
from typing import Optional, List
from app.domain.exceptions import DomainError


class InputValidationError(DomainError):
    """Error de validación de entrada"""
    pass


class InputValidator:
    """
    Validador genérico para inputs del usuario.
    Proporciona métodos para validar diferentes tipos de datos.
    """
    
    @staticmethod
    def validate_string(
        value: Optional[str],
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required: bool = True,
        pattern: Optional[re.Pattern] = None,
        allow_empty: bool = False
    ) -> str:
        """
        Valida un string.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo (para mensajes de error)
            min_length: Longitud mínima
            max_length: Longitud máxima
            required: Si es requerido
            pattern: Patrón regex para validar formato
            allow_empty: Permitir string vacío
            
        Returns:
            str: Valor validado y limpiado
            
        Raises:
            InputValidationError: Si la validación falla
        """
        # Verificar requerido
        if required and (value is None or (isinstance(value, str) and not value.strip() and not allow_empty)):
            raise InputValidationError(f"{field_name} es requerido")
        
        # Si no es requerido y está vacío, retornar vacío
        if not required and (not value or (isinstance(value, str) and not value.strip())):
            return ""
        
        # Convertir a string
        str_value = str(value).strip()
        
        # Validar longitud mínima
        if min_length and len(str_value) < min_length:
            raise InputValidationError(
                f"{field_name} debe tener al menos {min_length} caracteres"
            )
        
        # Validar longitud máxima
        if max_length and len(str_value) > max_length:
            raise InputValidationError(
                f"{field_name} no puede tener más de {max_length} caracteres"
            )
        
        # Validar patrón
        if pattern and not pattern.match(str_value):
            raise InputValidationError(
                f"{field_name} no tiene un formato válido"
            )
        
        return str_value
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Sanitiza HTML removiendo tags y caracteres peligrosos.
        
        Args:
            value: String a sanitizar
            
        Returns:
            str: String sanitizado
        """
        if not value:
            return ""
        
        # Remover caracteres peligrosos
        dangerous = ['<', '>', '"', "'", '&', ';', '\\']
        sanitized = value
        
        for char in dangerous:
            sanitized = sanitized.replace(char, '')
        
        return sanitized
    
    @staticmethod
    def validate_integer(
        value: Optional[str],
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True
    ) -> int:
        """
        Valida un entero.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            required: Si es requerido
            
        Returns:
            int: Valor entero validado
            
        Raises:
            InputValidationError: Si la validación falla
        """
        if required and (value is None or (isinstance(value, str) and not value.strip())):
            raise InputValidationError(f"{field_name} es requerido")
        
        if not required and (not value or (isinstance(value, str) and not value.strip())):
            return 0
        
        try:
            int_value = int(str(value).strip())
        except (ValueError, TypeError):
            raise InputValidationError(f"{field_name} debe ser un número entero válido")
        
        # Validar rango
        if min_value is not None and int_value < min_value:
            raise InputValidationError(
                f"{field_name} debe ser mayor o igual a {min_value}"
            )
        
        if max_value is not None and int_value > max_value:
            raise InputValidationError(
                f"{field_name} debe ser menor o igual a {max_value}"
            )
        
        return int_value
    
    @staticmethod
    def validate_choice(
        value: Optional[str],
        field_name: str,
        allowed_choices: List[str],
        required: bool = True
    ) -> str:
        """
        Valida que el valor esté en una lista de opciones permitidas.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            allowed_choices: Lista de valores permitidos
            required: Si es requerido
            
        Returns:
            str: Valor validado
            
        Raises:
            InputValidationError: Si la validación falla
        """
        if required and (value is None or (isinstance(value, str) and not value.strip())):
            raise InputValidationError(f"{field_name} es requerido")
        
        if not required and (not value or (isinstance(value, str) and not value.strip())):
            return ""
        
        str_value = str(value).strip()
        
        if str_value not in allowed_choices:
            raise InputValidationError(
                f"{field_name} debe ser uno de: {', '.join(allowed_choices)}"
            )
        
        return str_value














