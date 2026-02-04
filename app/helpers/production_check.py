"""
Helper para verificar si estamos en producción y evitar uso de archivos locales
"""
import os


def is_production():
    """
    Verifica si la aplicación está corriendo en producción.
    
    Returns:
        bool: True si FLASK_ENV=production, False en desarrollo local
    """
    try:
        return os.environ.get('FLASK_ENV', '').lower() == 'production'
    except Exception:
        return False


def get_safe_instance_path():
    """
    Obtiene instance_path solo si NO estamos en producción.
    En producción retorna None.
    
    Returns:
        str or None: Ruta de instance_path o None si está en producción
    """
    if is_production():
        return None
    
    try:
        from flask import current_app
        if current_app:
            return current_app.config.get('INSTANCE_PATH')
    except RuntimeError:
        # No hay contexto de aplicación
        pass
    
    return None


def ensure_not_production(operation_name="Esta operación"):
    """
    Verifica que NO estamos en producción. Si estamos en producción, lanza una excepción.
    
    Args:
        operation_name: Nombre de la operación para el mensaje de error
        
    Raises:
        RuntimeError: Si estamos en producción
    """
    if is_production():
        raise RuntimeError(
            f"{operation_name} no está disponible en producción. "
            "En producción no se usan archivos locales."
        )




