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

from app import create_app

application = create_app()
