"""
Entrada WSGI para cPanel (Passenger).
cPanel Setup Python App busca este archivo por defecto.
"""
import sys
import os

# Raíz del proyecto = directorio donde está este archivo
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Cambiar al directorio del proyecto (por si cPanel ejecuta desde otro sitio)
os.chdir(project_root)

# Asegurar entorno de producción
if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'production'

from app import create_app

# Crear la aplicación
application = create_app()
