#!/usr/bin/env python3
"""
Script para ejecutar la aplicación Flask localmente
"""
import os
import sys
import secrets

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno ANTES de importar la app
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    # En local, forzar override para que el .env mande (útil con reloader)
    load_dotenv(env_path, override=True)
    print(f"✅ Variables de entorno cargadas desde: {env_path}")
else:
    # Intentar cargar desde directorio actual o padres
    load_dotenv(override=True)
    print("⚠️  Archivo .env no encontrado en raíz, buscando en directorios padres...")

def _env_flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def _reset_local_state_if_needed():
    """
    En local: limpiar persistencia para "olvidar todo" en cada arranque.
    - Borra SQLite local (instance/bimba.db)
    - Borra admin users cache (instance/.admin_users.json)
    - Borra logs locales
    - Rota FLASK_SECRET_KEY para invalidar sesiones/cookies
    """
    local_only = _env_flag("LOCAL_ONLY", True)
    flask_env = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    reset_on_start = _env_flag("RESET_LOCAL_STATE_ON_START", True)

    if not (local_only and reset_on_start and flask_env != "production"):
        return

    root_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(root_dir, "instance")
    logs_dir = os.path.join(root_dir, "logs")

    paths_to_remove = [
        os.path.join(instance_dir, "bimba.db"),
        os.path.join(instance_dir, ".admin_users.json"),
        os.path.join(logs_dir, "app.log"),
        os.path.join(logs_dir, "getnet.log"),
    ]

    removed_any = False
    for p in paths_to_remove:
        try:
            if os.path.exists(p):
                os.remove(p)
                removed_any = True
        except Exception as e:
            print(f"⚠️  No se pudo borrar {p}: {e}")

    # Rotar secret key para invalidar sesiones previas (menu gate, etc.)
    os.environ["FLASK_SECRET_KEY"] = secrets.token_urlsafe(32)

    if removed_any:
        print("🧹 Reset local: BD/estado/logs limpiados para iniciar en limpio")
    else:
        print("🧹 Reset local: sin archivos que limpiar, iniciando en limpio")

_reset_local_state_if_needed()

from app import create_app, socketio

if __name__ == '__main__':
    # Crear la aplicación (ya carga .env internamente, pero lo hacemos antes por seguridad)
    app = create_app()

    # Seed opcional de datos demo en local (útil cuando también reseteamos estado al arrancar)
    try:
        def _should_run_seed() -> bool:
            # En modo reloader, ejecutar solo en el proceso "main" de werkzeug
            debug_enabled = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
            if debug_enabled and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
                return False
            return _env_flag("SEED_LOCAL_DATA_ON_START", False)

        if _should_run_seed():
            from scripts.seed_local_demo_data import seed_local_demo_data
            with app.app_context():
                seed_local_demo_data()
    except Exception as e:
        print(f"⚠️  Seed local demo falló (continuando igual): {e}")
    
    # Configurar para desarrollo local (sobrescribir si es necesario)
    app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'development')
    app.config['FLASK_DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Verificar configuración crítica
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not database_url or 'sqlite' in database_url.lower():
        print("⚠️  ADVERTENCIA: No se detectó DATABASE_URL de PostgreSQL. Verifica tu archivo .env")
    else:
        print(f"✅ Base de datos configurada: {database_url.split('@')[-1] if '@' in database_url else 'PostgreSQL'}")
    
    # Obtener puerto de variable de entorno o usar 5001 por defecto
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '127.0.0.1')
    
    print("=" * 60)
    print("🚀 Iniciando aplicación Flask local")
    print("=" * 60)
    print(f"📍 URL: http://{host}:{port}")
    print(f"🔧 Entorno: {app.config.get('FLASK_ENV', 'development')}")
    print(f"🐛 Debug: {app.config.get('FLASK_DEBUG', False)}")
    print("=" * 60)
    print()
    
    try:
        # Ejecutar con SocketIO (necesario para WebSockets)
        socketio.run(
            app,
            host=host,
            port=port,
            debug=app.config.get('FLASK_DEBUG', True),
            allow_unsafe_werkzeug=True  # Para desarrollo
        )
    except KeyboardInterrupt:
        print("\n\n👋 Deteniendo servidor...")
        sys.exit(0)




