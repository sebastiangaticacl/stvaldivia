"""
Sistema de versionado de la aplicación
Actualiza automáticamente la versión basándose en la fecha de última modificación
"""
import os
from datetime import datetime
from flask import current_app


# Versión base de la aplicación (se actualiza automáticamente)
APP_VERSION_BASE = "2.1"
APP_VERSION_PATCH = None  # None = usar git o fecha automáticamente. "35" = fijar en v2.1.35
APP_NAME = "BIMBA POS"


def _get_latest_code_modification():
    """
    Obtiene la fecha de última modificación del código fuente
    
    Returns:
        datetime: Fecha de última modificación
    """
    try:
        # Directorio raíz de la aplicación
        app_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Archivos clave a verificar
        key_files = [
            os.path.join(app_dir, '__init__.py'),
            os.path.join(app_dir, 'routes.py'),
            os.path.join(app_dir, 'config.py'),
        ]
        
        # También verificar directorios importantes
        key_dirs = [
            os.path.join(app_dir, 'models'),
            os.path.join(app_dir, 'helpers'),
            os.path.join(app_dir, 'application'),
        ]
        
        latest_time = datetime.fromtimestamp(0)
        
        # Verificar archivos clave
        for file_path in key_files:
            if os.path.exists(file_path):
                mod_time = os.path.getmtime(file_path)
                file_time = datetime.fromtimestamp(mod_time)
                if file_time > latest_time:
                    latest_time = file_time
        
        # Verificar archivos en directorios clave (solo .py)
        for dir_path in key_dirs:
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                mod_time = os.path.getmtime(file_path)
                                file_time = datetime.fromtimestamp(mod_time)
                                if file_time > latest_time:
                                    latest_time = file_time
                            except:
                                continue
        
        return latest_time
    except Exception:
        # Si hay error, usar fecha actual
        return datetime.now()


def _get_git_version():
    """
    Intenta obtener versión desde Git (si está disponible)
    
    Returns:
        str|None: Versión desde git o None
    """
    try:
        import subprocess
        app_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Verificar si es un repositorio git
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            # Obtener número de commits
            commit_count = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if commit_count.returncode == 0:
                count = commit_count.stdout.strip()
                # Obtener hash corto
                hash_result = subprocess.run(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    cwd=app_dir,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if hash_result.returncode == 0:
                    short_hash = hash_result.stdout.strip()
                    return f"{APP_VERSION_BASE}.{count}-{short_hash[:7]}"
    except:
        pass
    
    return None


def get_app_version():
    """
    Obtiene la versión de la aplicación
    Formato: MAJOR.MINOR.PATCH (ej: 2.1.35)
    
    Prioridad:
    1. APP_VERSION_PATCH si está definido (versión fija)
    2. Versión desde git (si está disponible)
    3. Versión basada en fecha de modificación (fallback)
    
    Returns:
        str: Versión de la aplicación
    """
    # Prioridad 1: Si hay una versión específica definida, usarla
    if APP_VERSION_PATCH:
        return f"{APP_VERSION_BASE}.{APP_VERSION_PATCH}"
    
    # Prioridad 2: Intentar obtener versión desde git
    git_version = _get_git_version()
    if git_version:
        # Si viene de git, formatear también en decimales simples
        # git_version viene como "2.1.150-a1b2c3d", extraer solo el número
        try:
            if '-' in git_version:
                parts = git_version.split('-')
                if len(parts) >= 2:
                    # Extraer número de commits
                    commit_part = parts[0].split('.')[-1] if '.' in parts[0] else parts[0]
                    return f"{APP_VERSION_BASE}.{commit_part}"
        except:
            pass
        return git_version
    
    # Prioridad 3: Si no hay git, usar versión basada en fecha de modificación
    # Genera un número incremental simple basado en minutos desde fecha base
    try:
        latest_mod = _get_latest_code_modification()
        
        # Calcular minutos desde fecha base (2025-01-01 00:00:00)
        base_date = datetime(2025, 1, 1, 0, 0, 0)
        time_diff = latest_mod - base_date
        minutes_diff = int(time_diff.total_seconds() / 60)
        
        # Usar minutos como patch version (incrementa con cada cambio)
        # Esto da números como: 2.1.0, 2.1.1, 2.1.2, ..., 2.1.483840, etc.
        # Cada minuto desde el epoch = un incremento de versión
        patch_version = max(0, minutes_diff)
        
        return f"{APP_VERSION_BASE}.{patch_version}"
    except:
        # Fallback a versión base
        return f"{APP_VERSION_BASE}.0"


def get_app_name():
    """
    Obtiene el nombre de la aplicación
    
    Returns:
        str: Nombre de la aplicación
    """
    return APP_NAME


def get_build_info():
    """
    Obtiene información de build (fecha de última modificación)
    
    Returns:
        dict: Información de build
    """
    try:
        latest_mod = _get_latest_code_modification()
        build_date = latest_mod.strftime('%Y-%m-%d')
        build_time = latest_mod.strftime('%H:%M:%S')
    except:
        build_date = datetime.now().strftime('%Y-%m-%d')
        build_time = datetime.now().strftime('%H:%M:%S')
    
    return {
        'version': get_app_version(),
        'name': APP_NAME,
        'build_date': build_date,
        'build_time': build_time
    }


def get_version_string():
    """
    Obtiene string completo de versión para mostrar
    
    Returns:
        str: String de versión formateado
    """
    build_info = get_build_info()
    return f"v{build_info['version']}"


def get_full_version_string():
    """
    Obtiene string completo de versión con fecha
    
    Returns:
        str: String de versión completo
    """
    build_info = get_build_info()
    return f"{build_info['name']} v{build_info['version']} ({build_info['build_date']})"

