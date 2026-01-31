"""
Validador Estricto para Sale ID
Valida y normaliza IDs de venta con formato: BMB 123, B 123, POS 123, o solo números
"""
import re
from typing import Optional, Tuple
from app.domain.exceptions import DomainError


class SaleIdValidationError(DomainError):
    """Error de validación de Sale ID"""
    pass


class SaleIdValidator:
    """
    Validador estricto para IDs de venta.
    
    Formatos aceptados:
    - "BMB 123" o "BMB123" -> BMB 123
    - "B 123" o "B123" -> B 123 (kiosco)
    - "POS 123" o "POS123" -> BMB 123
    - "123" -> BMB 123
    """
    
    # Patrones permitidos
    PATTERN_BMB = re.compile(r'^BMB\s*(\d+)$', re.IGNORECASE)
    PATTERN_B = re.compile(r'^B\s*(\d+)$', re.IGNORECASE)
    PATTERN_POS = re.compile(r'^POS\s*(\d+)$', re.IGNORECASE)
    PATTERN_NUMERIC = re.compile(r'^(\d+)$')
    PATTERN_MIXED = re.compile(r'^[A-Z\s]*(\d+)$', re.IGNORECASE)
    
    # Caracteres permitidos (whitelist)
    ALLOWED_CHARS = re.compile(r'^[A-Z0-9\s]+$', re.IGNORECASE)
    
    # Longitud máxima
    MAX_LENGTH = 50
    MIN_LENGTH = 1
    
    @staticmethod
    def validate_and_normalize(sale_id: str) -> Tuple[str, str]:
        """
        Valida y normaliza un sale_id.
        
        Args:
            sale_id: ID de venta a validar
            
        Returns:
            Tuple[str, str]: (sale_id_canonical, numeric_id)
                - sale_id_canonical: Formato normalizado (ej: "BMB 123")
                - numeric_id: Solo el número (ej: "123")
                
        Raises:
            SaleIdValidationError: Si el sale_id es inválido
        """
        if not sale_id:
            raise SaleIdValidationError("sale_id no puede estar vacío")
        
        # 1. Limpiar espacios
        cleaned = sale_id.strip()
        
        # 2. Validar longitud
        if len(cleaned) < SaleIdValidator.MIN_LENGTH:
            raise SaleIdValidationError(f"sale_id demasiado corto (mínimo {SaleIdValidator.MIN_LENGTH} caracter)")
        
        if len(cleaned) > SaleIdValidator.MAX_LENGTH:
            raise SaleIdValidationError(f"sale_id demasiado largo (máximo {SaleIdValidator.MAX_LENGTH} caracteres)")
        
        # 3. Validar caracteres permitidos (whitelist)
        if not SaleIdValidator.ALLOWED_CHARS.match(cleaned):
            raise SaleIdValidationError(
                f"sale_id contiene caracteres inválidos. Solo se permiten letras, números y espacios"
            )
        
        # 4. Normalizar a mayúsculas
        normalized = cleaned.upper()
        
        # 5. Intentar detectar y normalizar formato
        numeric_id = None
        canonical = None
        
        # Intentar BMB
        match = SaleIdValidator.PATTERN_BMB.match(normalized)
        if match:
            numeric_id = match.group(1)
            canonical = f"BMB {numeric_id}"
            return canonical, numeric_id
        
        # Intentar B (kiosco)
        match = SaleIdValidator.PATTERN_B.match(normalized)
        if match:
            numeric_id = match.group(1)
            canonical = f"B {numeric_id}"
            return canonical, numeric_id
        
        # Intentar POS
        match = SaleIdValidator.PATTERN_POS.match(normalized)
        if match:
            numeric_id = match.group(1)
            canonical = f"BMB {numeric_id}"  # POS se convierte a BMB
            return canonical, numeric_id
        
        # Intentar solo números
        match = SaleIdValidator.PATTERN_NUMERIC.match(normalized)
        if match:
            numeric_id = match.group(1)
            canonical = f"BMB {numeric_id}"
            return canonical, numeric_id
        
        # Intentar extraer números de formato mixto
        match = SaleIdValidator.PATTERN_MIXED.match(normalized)
        if match:
            numeric_id = match.group(1)
            # Si tiene prefijo reconocible, mantenerlo; si no, usar BMB
            if normalized.startswith('B ') or normalized.startswith('B'):
                canonical = f"B {numeric_id}"
            else:
                canonical = f"BMB {numeric_id}"
            return canonical, numeric_id
        
        # Si no coincide con ningún patrón, error
        raise SaleIdValidationError(
            f"Formato de sale_id inválido: '{sale_id}'. "
            f"Formatos aceptados: 'BMB 123', 'B 123', 'POS 123', o '123'"
        )
    
    @staticmethod
    def sanitize_input(user_input: str) -> str:
        """
        Sanitiza input del usuario removiendo caracteres peligrosos.
        
        Args:
            user_input: Input del usuario
            
        Returns:
            str: Input sanitizado
        """
        if not user_input:
            return ""
        
        # Remover caracteres peligrosos para inyección
        dangerous_chars = ['<', '>', '"', "'", ';', '\\', '/', '&', '|', '`', '$']
        sanitized = user_input
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limitar longitud
        sanitized = sanitized[:SaleIdValidator.MAX_LENGTH]
        
        return sanitized.strip()
    
    @staticmethod
    def is_valid(sale_id: str) -> bool:
        """
        Verifica si un sale_id es válido sin lanzar excepción.
        
        Args:
            sale_id: ID de venta a verificar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        try:
            SaleIdValidator.validate_and_normalize(sale_id)
            return True
        except SaleIdValidationError:
            return False














