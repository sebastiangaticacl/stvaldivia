"""
Utilidades para manejo de zona horaria de Chile
"""
from datetime import datetime
import pytz

# Zona horaria de Chile
CHILE_TZ = pytz.timezone('America/Santiago')

def get_chile_time():
    """
    Obtiene la hora actual en zona horaria de Chile
    
    Returns:
        datetime: Hora actual en Chile
    """
    return datetime.now(CHILE_TZ)

def utc_to_chile(utc_dt):
    """
    Convierte un datetime UTC a hora de Chile
    
    Args:
        utc_dt: datetime en UTC (puede ser naive o aware)
    
    Returns:
        datetime: datetime en zona horaria de Chile
    """
    if utc_dt is None:
        return None
    
    # Si es naive, asumir UTC
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    
    # Convertir a Chile
    return utc_dt.astimezone(CHILE_TZ)

def chile_to_utc(chile_dt):
    """
    Convierte un datetime de Chile a UTC
    
    Args:
        chile_dt: datetime en hora de Chile (puede ser naive o aware)
    
    Returns:
        datetime: datetime en UTC
    """
    if chile_dt is None:
        return None
    
    # Si es naive, asumir que es hora de Chile
    if chile_dt.tzinfo is None:
        chile_dt = CHILE_TZ.localize(chile_dt)
    
    # Convertir a UTC
    return chile_dt.astimezone(pytz.UTC)

def format_chile_time(dt=None, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Formatea un datetime a string en hora de Chile
    
    Args:
        dt: datetime (si es None, usa hora actual)
        format_str: formato de salida
    
    Returns:
        str: datetime formateado
    """
    if dt is None:
        dt = get_chile_time()
    else:
        dt = utc_to_chile(dt) if dt.tzinfo else CHILE_TZ.localize(dt)
    
    return dt.strftime(format_str)

def format_date_spanish(date_str=None, dt=None):
    """
    Formatea una fecha al formato español DD/MM/YYYY
    
    Args:
        date_str: string de fecha en formato YYYY-MM-DD (opcional)
        dt: datetime object (opcional)
    
    Returns:
        str: fecha formateada como DD/MM/YYYY
    """
    if dt:
        # Si es datetime, convertir a Chile si es necesario
        if dt.tzinfo:
            dt = utc_to_chile(dt) if dt.tzinfo == pytz.UTC else dt.astimezone(CHILE_TZ)
        else:
            dt = CHILE_TZ.localize(dt)
        return dt.strftime('%d/%m/%Y')
    elif date_str:
        # Si es string, parsear y formatear
        try:
            # Intentar parsear formato YYYY-MM-DD
            if len(date_str) >= 10:
                year, month, day = date_str[:10].split('-')
                return f"{day}/{month}/{year}"
            return date_str
        except:
            return date_str
    else:
        # Si no hay parámetros, usar fecha actual
        return get_chile_time().strftime('%d/%m/%Y')

