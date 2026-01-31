"""
Excepciones de Dominio
Excepciones específicas del negocio.
"""


class DomainError(Exception):
    """Excepción base de dominio"""
    pass


class ShiftNotOpenError(DomainError):
    """Error: No hay un turno abierto"""
    pass


class ShiftAlreadyOpenError(DomainError):
    """Error: Ya hay un turno abierto"""
    pass


class DeliveryValidationError(DomainError):
    """Error: Validación de entrega fallida"""
    pass


class FraudDetectedError(DomainError):
    """Error: Fraude detectado"""
    def __init__(self, message: str, fraud_type: str, details: dict = None):
        super().__init__(message)
        self.fraud_type = fraud_type
        self.details = details or {}









