import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production


ADMIN_USERS_FILE = '.admin_users.json'


def get_admin_users_file():
    """Obtiene la ruta del archivo de usuarios admin"""
    # Permitir en producción si el archivo existe (para compatibilidad)
    instance_path = None
    try:
        if not is_production():
            ensure_not_production("El sistema de usuarios admin desde archivo")
            instance_path = get_safe_instance_path() or current_app.instance_path
        else:
            # En producción, intentar usar instance_path si está disponible
            try:
                instance_path = get_safe_instance_path() or current_app.instance_path
            except:
                # Si no hay contexto, usar ruta por defecto
                instance_path = 'instance'
    except:
        # Si hay error, intentar obtener instance_path de todas formas
        try:
            instance_path = get_safe_instance_path() or current_app.instance_path
        except:
            instance_path = 'instance'
    
    return os.path.join(instance_path, ADMIN_USERS_FILE)


def load_admin_users():
    """Carga los usuarios admin desde el archivo"""
    users_file = get_admin_users_file()
    
    if not os.path.exists(users_file):
        # Crear usuarios por defecto
        default_users = {
            'sebagatica': {
                'password_hash': generate_password_hash('12345', method='pbkdf2:sha256'),
                'username': 'sebagatica'
            }
        }
        save_admin_users(default_users)
        return default_users
    
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        current_app.logger.error(f"Error al cargar usuarios admin: {e}")
        # Retornar usuarios por defecto si hay error
        return {
            'sebagatica': {
                'password_hash': generate_password_hash('12345', method='pbkdf2:sha256'),
                'username': 'sebagatica'
            }
        }


def save_admin_users(users):
    """Guarda los usuarios admin en el archivo"""
    users_file = get_admin_users_file()
    
    try:
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        current_app.logger.error(f"Error al guardar usuarios admin: {e}")
        return False


def verify_admin_user(username, password):
    """Verifica si el usuario y contraseña son correctos"""
    users = load_admin_users()
    
    if username not in users:
        return False
    
    user = users[username]
    stored_hash = user.get('password_hash')
    
    if not stored_hash:
        return False
    
    # Verificar contraseña - SOLO con hash, sin fallback inseguro
    if stored_hash.startswith('pbkdf2:'):
        return check_password_hash(stored_hash, password)
    else:
        # Si no tiene hash válido, rechazar acceso
        # El usuario debe resetear su password
        current_app.logger.warning(f"⚠️ Usuario {username} tiene password sin hash válido. Acceso denegado.")
        return False


def create_admin_user(username, password):
    """Crea un nuevo usuario admin"""
    users = load_admin_users()
    
    if username in users:
        return False  # Usuario ya existe
    
    users[username] = {
        'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
        'username': username
    }
    
    return save_admin_users(users)


def update_admin_user_password(username, new_password):
    """Actualiza la contraseña de un usuario admin"""
    users = load_admin_users()
    
    if username not in users:
        return False
    
    users[username]['password_hash'] = generate_password_hash(new_password, method='pbkdf2:sha256')
    return save_admin_users(users)


def delete_admin_user(username):
    """Elimina un usuario admin"""
    users = load_admin_users()
    
    if username not in users:
        return False
    
    if len(users) <= 1:
        return False  # No se puede eliminar el último usuario
    
    del users[username]
    return save_admin_users(users)


def list_admin_users():
    """Lista todos los usuarios admin (sin contraseñas)"""
    users = load_admin_users()
    return [{'username': username} for username in users.keys()]





