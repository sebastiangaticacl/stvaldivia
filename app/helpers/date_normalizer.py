"""
Normalizador de fechas para reducir bugs por formatos inconsistentes
Solo normaliza en puntos de escritura, NO cambia modelos ni columnas
"""
from datetime import datetime
from flask import current_app
from typing import Optional


def normalize_shift_date(value) -> Optional[str]:
    """
    Normaliza una fecha a formato YYYY-MM-DD.
    
    Acepta:
    - String en formato YYYY-MM-DD
    - String en formato DD/MM/YYYY
    - String en formato YYYY/MM/DD
    - datetime.date o datetime.datetime
    
    Returns:
        str: Fecha en formato YYYY-MM-DD o None si no se puede normalizar
    
    Logs warning si el formato es inválido pero NO lanza excepción.
    """
    if value is None:
        return None
    
    # Si es datetime.date o datetime.datetime
    if isinstance(value, datetime):
        return value.date().strftime('%Y-%m-%d')
    if hasattr(value, 'strftime'):  # datetime.date
        return value.strftime('%Y-%m-%d')
    
    # Si es string, intentar parsear
    if isinstance(value, str):
        value = value.strip()
        
        # Ya está en formato YYYY-MM-DD
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            try:
                # Validar que sea fecha válida
                datetime.strptime(value, '%Y-%m-%d')
                return value
            except ValueError:
                pass
        
        # Intentar formatos comunes
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Si no se pudo parsear, loggear warning pero retornar None
        try:
            current_app.logger.warning(
                f"Formato de fecha inválido: '{value}'. "
                "Se esperaba YYYY-MM-DD, DD/MM/YYYY o similar."
            )
        except:
            pass  # Si no hay contexto de app, continuar silenciosamente
        
        return None
    
    # Tipo no reconocido
    try:
        current_app.logger.warning(
            f"Tipo de fecha no reconocido: {type(value)}. "
            "Se esperaba string o datetime."
        )
    except:
        pass
    
    return None

