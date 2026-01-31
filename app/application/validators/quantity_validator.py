"""
Validador de Cantidades
Validación estricta para cantidades de productos
"""
from typing import Optional
from app.application.validators.input_validator import InputValidator, InputValidationError


class QuantityValidationError(InputValidationError):
    """Error de validación de cantidad"""
    pass


class QuantityValidator:
    """
    Validador para cantidades de productos.
    """
    
    MIN_QUANTITY = 1
    MAX_QUANTITY = 1000  # Límite razonable para prevenir errores
    
    @staticmethod
    def validate(quantity: Optional[str], field_name: str = "Cantidad") -> int:
        """
        Valida una cantidad.
        
        Args:
            quantity: Cantidad a validar (puede ser string o int)
            field_name: Nombre del campo para mensajes de error
            
        Returns:
            int: Cantidad validada
            
        Raises:
            QuantityValidationError: Si la validación falla
        """
        try:
            qty = InputValidator.validate_integer(
                quantity,
                field_name=field_name,
                min_value=QuantityValidator.MIN_QUANTITY,
                max_value=QuantityValidator.MAX_QUANTITY,
                required=True
            )
            
            return qty
            
        except InputValidationError as e:
            raise QuantityValidationError(str(e))
    
    @staticmethod
    def validate_with_max(
        quantity: Optional[str],
        max_allowed: int,
        field_name: str = "Cantidad"
    ) -> int:
        """
        Valida una cantidad con un máximo específico.
        
        Args:
            quantity: Cantidad a validar
            max_allowed: Cantidad máxima permitida
            field_name: Nombre del campo
            
        Returns:
            int: Cantidad validada
            
        Raises:
            QuantityValidationError: Si la validación falla
        """
        if max_allowed < QuantityValidator.MIN_QUANTITY:
            raise QuantityValidationError(
                f"La cantidad máxima permitida ({max_allowed}) es menor que el mínimo ({QuantityValidator.MIN_QUANTITY})"
            )
        
        try:
            qty = InputValidator.validate_integer(
                quantity,
                field_name=field_name,
                min_value=QuantityValidator.MIN_QUANTITY,
                max_value=min(max_allowed, QuantityValidator.MAX_QUANTITY),
                required=True
            )
            
            if qty > max_allowed:
                raise QuantityValidationError(
                    f"{field_name} ({qty}) excede la cantidad máxima permitida ({max_allowed})"
                )
            
            return qty
            
        except InputValidationError as e:
            raise QuantityValidationError(str(e))














