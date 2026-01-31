"""
Filtros personalizados para templates Jinja2
"""
from datetime import datetime


def format_datetime(value, date_format='%d/%m/%Y', time_format='%H:%M'):
    """
    Formatea un datetime o string a formato legible
    """
    if not value:
        return '-'
    
    # Si es string, intentar parsearlo
    if isinstance(value, str):
        try:
            # Intentar formato ISO
            if 'T' in value:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif ' ' in value:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            else:
                return value[:10] if len(value) > 10 else value
        except:
            return value
    elif hasattr(value, 'strftime'):
        dt = value
    else:
        return str(value)
    
    return dt.strftime(f'{date_format} {time_format}')


def format_date(value, date_format='%d/%m/%Y'):
    """Formatea solo la fecha"""
    if not value:
        return '-'
    
    if isinstance(value, str):
        try:
            if 'T' in value:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif ' ' in value:
                dt = datetime.strptime(value.split(' ')[0], '%Y-%m-%d')
            else:
                return value[:10] if len(value) > 10 else value
        except:
            return value[:10] if len(value) > 10 else value
    elif hasattr(value, 'strftime'):
        dt = value
    else:
        return str(value)
    
    return dt.strftime(date_format)


def format_time(value, time_format='%H:%M'):
    """Formatea solo la hora"""
    if not value:
        return '-'
    
    if isinstance(value, str):
        try:
            if 'T' in value:
                time_part = value.split('T')[1][:5] if len(value.split('T')) > 1 else value[:5]
                return time_part
            elif ' ' in value:
                time_part = value.split(' ')[1][:5] if len(value.split(' ')) > 1 else value[:5]
                return time_part
            else:
                return value[:5] if len(value) > 5 else value
        except:
            return value[:5] if len(value) > 5 else value
    elif hasattr(value, 'strftime'):
        return value.strftime(time_format)
    else:
        return str(value)













