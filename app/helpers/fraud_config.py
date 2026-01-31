import os
import json
from flask import current_app
from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production

DEFAULT_FRAUD_CONFIG = {
    'max_hours_old_ticket': 24,
    'max_delivery_attempts': 3,
    'disabled_registers': []  # Lista de IDs de cajas deshabilitadas
}

CONFIG_FILE = 'fraud_config.json'


def get_fraud_config_file():
    """Obtiene la ruta del archivo de configuración de fraude"""
    if is_production():
        return None  # En producción no se usan archivos
    
    # Solo en desarrollo
    instance_path = get_safe_instance_path()
    if not instance_path:
        instance_path = os.path.join(os.getcwd(), 'instance')
        os.makedirs(instance_path, exist_ok=True)
    
    return os.path.join(instance_path, CONFIG_FILE)


def load_fraud_config():
    """Carga la configuración de fraude"""
    # En producción, usar valores por defecto o desde variables de entorno/base de datos
    if is_production():
        config = DEFAULT_FRAUD_CONFIG.copy()
        
        # Intentar cargar desde variables de entorno
        max_hours = os.environ.get('FRAUD_MAX_HOURS_OLD_TICKET')
        if max_hours:
            try:
                config['max_hours_old_ticket'] = int(max_hours)
            except:
                pass
        
        max_attempts = os.environ.get('FRAUD_MAX_DELIVERY_ATTEMPTS')
        if max_attempts:
            try:
                config['max_delivery_attempts'] = int(max_attempts)
            except:
                pass
        
        # En producción, cargar disabled_registers desde base de datos si existe
        try:
            from app.models.pos_models import PosRegister
            from flask import has_app_context, current_app
            from app import db
            
            # Intentar acceder a la base de datos solo si hay contexto de app
            if has_app_context():
                try:
                    disabled_registers = PosRegister.query.filter_by(
                        is_active=False
                    ).all()
                    config['disabled_registers'] = [str(reg.id) for reg in disabled_registers]
                except Exception as db_error:
                    # Si hay error de BD, usar lista vacía
                    try:
                        current_app.logger.warning(f"No se pudo cargar disabled_registers desde BD: {db_error}")
                    except:
                        pass
                    config['disabled_registers'] = []
            else:
                # Si no hay contexto de app, usar lista vacía
                config['disabled_registers'] = []
        except Exception as e:
            # Si no se puede cargar desde BD, usar lista vacía
            config['disabled_registers'] = []
        
        return config
    
    # En desarrollo, cargar desde archivo
    config_file = get_fraud_config_file()
    
    if not config_file or not os.path.exists(config_file):
        # Crear archivo con configuración por defecto
        save_fraud_config(DEFAULT_FRAUD_CONFIG)
        return DEFAULT_FRAUD_CONFIG.copy()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Mergear con defaults para asegurar que todas las keys existan
            merged = DEFAULT_FRAUD_CONFIG.copy()
            merged.update(config)
            return merged
    except Exception as e:
        try:
            current_app.logger.error(f"Error al cargar configuración de fraude: {e}")
        except:
            pass
        return DEFAULT_FRAUD_CONFIG.copy()


def save_fraud_config(config):
    """Guarda la configuración de fraude"""
    # En producción, guardar en base de datos en lugar de archivo
    if is_production():
        try:
            from app.models.pos_models import PosRegister
            from flask import has_app_context, current_app
            from app import db
            
            # Solo guardar si hay contexto de app
            if not has_app_context():
                return False
            
            # Guardar disabled_registers en la base de datos
            disabled_registers = config.get('disabled_registers', [])
            
            # Deshabilitar las cajas especificadas
            for reg_id in disabled_registers:
                try:
                    reg = PosRegister.query.filter_by(id=int(reg_id)).first()
                    if reg:
                        reg.is_active = False
                except:
                    pass
            
            # Habilitar las cajas que no están en la lista
            all_registers = PosRegister.query.all()
            for reg in all_registers:
                if str(reg.id) not in disabled_registers:
                    reg.is_active = True
            
            db.session.commit()
            return True
        except Exception as e:
            try:
                if has_app_context():
                    current_app.logger.error(f"Error al guardar configuración de fraude en BD: {e}")
            except:
                pass
            return False
    
    # En desarrollo, guardar en archivo
    config_file = get_fraud_config_file()
    if not config_file:
        return False
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        try:
            current_app.logger.error(f"Error al guardar configuración de fraude: {e}")
        except:
            pass
        return False




