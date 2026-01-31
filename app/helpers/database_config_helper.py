"""
Helper para gestionar la configuración de base de datos (dev/prod)
"""
import os
import logging
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

# Claves de configuración
DB_MODE_KEY = 'database_mode'  # 'dev' o 'prod'
DB_DEV_URL_KEY = 'database_dev_url'
DB_PROD_URL_KEY = 'database_prod_url'

def get_database_mode():
    """
    Obtiene el modo de base de datos actual ('dev' o 'prod')
    Por defecto usa 'prod' si no está configurado
    """
    if not has_app_context():
        # Si no hay contexto, usar variable de entorno o default
        return os.environ.get('DATABASE_MODE', 'prod')
    
    try:
        from app.models.system_config_models import SystemConfig
        mode = SystemConfig.get(DB_MODE_KEY, 'prod')
        return mode
    except Exception as e:
        logger.warning(f"Error al obtener modo de BD desde config: {e}")
        return os.environ.get('DATABASE_MODE', 'prod')

def set_database_mode(mode, updated_by=None):
    """
    Establece el modo de base de datos
    
    Args:
        mode: 'dev' o 'prod'
        updated_by: Usuario que hizo el cambio
    """
    if mode not in ['dev', 'prod']:
        raise ValueError("Modo debe ser 'dev' o 'prod'")
    
    if not has_app_context():
        logger.warning("No hay contexto de app, no se puede guardar configuración")
        return False
    
    try:
        from app.models.system_config_models import SystemConfig
        SystemConfig.set(
            DB_MODE_KEY, 
            mode, 
            description=f'Modo de base de datos: {mode}',
            updated_by=updated_by
        )
        logger.info(f"Modo de base de datos cambiado a: {mode} (por: {updated_by})")
        return True
    except Exception as e:
        logger.error(f"Error al guardar modo de BD: {e}", exc_info=True)
        return False

def get_database_url_for_mode(mode=None):
    """
    Obtiene la URL de base de datos para un modo específico
    
    Args:
        mode: 'dev' o 'prod'. Si es None, usa el modo actual
    """
    if mode is None:
        mode = get_database_mode()
    
    if not has_app_context():
        # Sin contexto, usar variables de entorno
        if mode == 'dev':
            return os.environ.get('DATABASE_DEV_URL') or os.environ.get('DATABASE_URL')
        else:
            return os.environ.get('DATABASE_PROD_URL') or os.environ.get('DATABASE_URL')
    
    try:
        from app.models.system_config_models import SystemConfig
        
        if mode == 'dev':
            url = SystemConfig.get(DB_DEV_URL_KEY)
            if not url:
                # Fallback a variable de entorno
                url = os.environ.get('DATABASE_DEV_URL') or os.environ.get('DATABASE_URL')
        else:
            url = SystemConfig.get(DB_PROD_URL_KEY)
            if not url:
                # Fallback a variable de entorno
                url = os.environ.get('DATABASE_PROD_URL') or os.environ.get('DATABASE_URL')
        
        return url
    except Exception as e:
        logger.warning(f"Error al obtener URL de BD desde config: {e}")
        return os.environ.get('DATABASE_URL')

def set_database_urls(dev_url=None, prod_url=None, updated_by=None):
    """
    Establece las URLs de base de datos para dev y prod
    
    Args:
        dev_url: URL de base de datos de desarrollo
        prod_url: URL de base de datos de producción
        updated_by: Usuario que hizo el cambio
    """
    if not has_app_context():
        logger.warning("No hay contexto de app, no se puede guardar configuración")
        return False
    
    try:
        from app.models.system_config_models import SystemConfig
        
        if dev_url:
            SystemConfig.set(
                DB_DEV_URL_KEY,
                dev_url,
                description='URL de base de datos de desarrollo',
                updated_by=updated_by
            )
            logger.info(f"URL de desarrollo guardada (por: {updated_by})")
        
        if prod_url:
            SystemConfig.set(
                DB_PROD_URL_KEY,
                prod_url,
                description='URL de base de datos de producción',
                updated_by=updated_by
            )
            logger.info(f"URL de producción guardada (por: {updated_by})")
        
        return True
    except Exception as e:
        logger.error(f"Error al guardar URLs de BD: {e}", exc_info=True)
        return False

def initialize_database_urls_from_env():
    """
    Inicializa las URLs de base de datos desde variables de entorno
    Se llama al inicio de la aplicación
    """
    import os
    
    if not has_app_context():
        return False
    
    try:
        dev_url = os.environ.get('DATABASE_DEV_URL')
        prod_url = os.environ.get('DATABASE_PROD_URL')
        
        if dev_url or prod_url:
            return set_database_urls(
                dev_url=dev_url,
                prod_url=prod_url,
                updated_by='system_init'
            )
        return False
    except Exception as e:
        logger.warning(f"Error al inicializar URLs desde ENV: {e}")
        return False

def get_current_database_info():
    """
    Obtiene información sobre la base de datos actual
    """
    mode = get_database_mode()
    url = get_database_url_for_mode(mode)
    
    # Ocultar password en el output
    safe_url = url
    if url and '@' in url:
        parts = url.split('@')
        if len(parts) == 2:
            creds = parts[0].split('://')
            if len(creds) == 2:
                user_pass = creds[1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    safe_url = f"{creds[0]}://{user}:***@{parts[1]}"
    
    return {
        'mode': mode,
        'url': safe_url,
        'url_raw': url
    }

