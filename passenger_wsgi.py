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

# Asegurar variables de entorno críticas si no están
# Esto es vital para que create_app() registre los blueprints con el prefijo correcto
if 'APPLICATION_ROOT' not in os.environ:
    os.environ['APPLICATION_ROOT'] = '/stvaldivia'
    
if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'production'

from app import create_app

class CPanelMiddleware(object):
    """
    Middleware para corregir problemas de ruta en cPanel/Passenger con subdirectorios.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # DEBUG: Escribir environment a un archivo para diagnóstico
        try:
            with open('request_debug.txt', 'a') as f:
                f.write(f"\n--- Request ---\n")
                f.write(f"SCRIPT_NAME: {environ.get('SCRIPT_NAME')}\n")
                f.write(f"PATH_INFO: {environ.get('PATH_INFO')}\n")
                f.write(f"REQUEST_URI: {environ.get('REQUEST_URI')}\n")
        except:
            pass
            
        script_name = environ.get('SCRIPT_NAME', '')
        
        # LOGICA ORIGINAL: restaurar script_name en path_info
        if script_name and script_name != '/':
            environ['PATH_INFO'] = script_name + environ.get('PATH_INFO', '')
            environ['SCRIPT_NAME'] = ''
            
        return self.app(environ, start_response)

application = create_app()
application.wsgi_app = CPanelMiddleware(application.wsgi_app)
