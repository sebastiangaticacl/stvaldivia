#!/usr/bin/env python3
"""
Script para ejecutar la aplicación Flask localmente
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno ANTES de importar la app
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ Variables de entorno cargadas desde: {env_path}")
else:
    # Intentar cargar desde directorio actual o padres
    load_dotenv()
    print("⚠️  Archivo .env no encontrado en raíz, buscando en directorios padres...")

from app import create_app, socketio

if __name__ == '__main__':
    # Crear la aplicación (ya carga .env internamente, pero lo hacemos antes por seguridad)
    app = create_app()
    
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




