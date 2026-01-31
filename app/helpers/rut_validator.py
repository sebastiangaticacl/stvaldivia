"""
Validador de RUT chileno
"""
import re
from typing import Tuple, Optional


def clean_rut(rut: str) -> str:
    """
    Limpia el RUT removiendo puntos y guiones
    
    Args:
        rut: RUT con o sin formato
        
    Returns:
        RUT limpio (solo números y dígito verificador)
    """
    if not rut:
        return ''
    # Remover puntos, guiones y espacios
    rut_clean = re.sub(r'[.\-\s]', '', rut.upper())
    return rut_clean


def validate_rut(rut: str) -> Tuple[bool, Optional[str]]:
    """
    Valida un RUT chileno
    
    Args:
        rut: RUT a validar (con o sin formato)
        
    Returns:
        Tuple (es_valido, mensaje_error)
    """
    rut_clean = clean_rut(rut)
    
    if not rut_clean:
        return False, "RUT no puede estar vacío"
    
    if len(rut_clean) < 8 or len(rut_clean) > 10:
        return False, "RUT debe tener entre 8 y 10 caracteres"
    
    # Separar número y dígito verificador
    if not rut_clean[-1].isdigit() and rut_clean[-1] not in ['K', 'k']:
        return False, "Dígito verificador inválido"
    
    rut_number = rut_clean[:-1]
    dv = rut_clean[-1].upper()
    
    # Validar que el número sea solo dígitos
    if not rut_number.isdigit():
        return False, "El RUT debe contener solo números y un dígito verificador"
    
    # Calcular dígito verificador
    calculated_dv = calculate_dv(rut_number)
    
    if calculated_dv != dv:
        return False, f"Dígito verificador inválido. Debería ser {calculated_dv}"
    
    return True, None


def calculate_dv(rut_number: str) -> str:
    """
    Calcula el dígito verificador de un RUT
    
    Args:
        rut_number: Número del RUT sin dígito verificador
        
    Returns:
        Dígito verificador calculado
    """
    rut_number = rut_number.replace('.', '').replace('-', '')
    
    # Algoritmo de cálculo del dígito verificador
    suma = 0
    multiplicador = 2
    
    # Recorrer de derecha a izquierda
    for i in range(len(rut_number) - 1, -1, -1):
        suma += int(rut_number[i]) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2
    
    resto = suma % 11
    dv = 11 - resto
    
    if dv == 11:
        return '0'
    elif dv == 10:
        return 'K'
    else:
        return str(dv)


def format_rut(rut: str) -> str:
    """
    Formatea un RUT con puntos y guión
    
    Args:
        rut: RUT sin formato
        
    Returns:
        RUT formateado (ej: 12.345.678-9)
    """
    rut_clean = clean_rut(rut)
    
    if not rut_clean or len(rut_clean) < 2:
        return rut_clean
    
    rut_number = rut_clean[:-1]
    dv = rut_clean[-1]
    
    # Agregar puntos cada 3 dígitos desde la derecha
    rut_formatted = ''
    for i, digit in enumerate(reversed(rut_number)):
        if i > 0 and i % 3 == 0:
            rut_formatted = '.' + rut_formatted
        rut_formatted = digit + rut_formatted
    
    return f"{rut_formatted}-{dv}"

