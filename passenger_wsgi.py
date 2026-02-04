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

class CPanelMiddleware(object):
    """
    Middleware para corregir problemas de ruta en cPanel/Passenger con subdirectorios.
    Si la app espera manejar la ruta completa (incluyendo /stvaldivia) vía APPLICATION_ROOT,
    necesitamos restaurar el prefijo que Passenger suele mover a SCRIPT_NAME.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Passenger puede poner '/stvaldivia' en SCRIPT_NAME y dejar PATH_INFO vacío o con la subruta.
        # Flask con APPLICATION_ROOT='/stvaldivia' espera que PATH_INFO contenga el prefijo.
        script_name = environ.get('SCRIPT_NAME', '')
        
        # Si SCRIPT_NAME tiene valor y PATH_INFO no lo incluye, lo prefijamos
        # Asumimos que la app quiere manejar todo el path
        if script_name and script_name != '/':
            environ['PATH_INFO'] = script_name + environ.get('PATH_INFO', '')
            # Limpiamos SCRIPT_NAME para que Flask no intente hacer routing relativo a él
            # OJO: Flask usa SCRIPT_NAME para generar URLs. Si lo borramos, url_for generará rutas sin prefijo?
            # Si APPLICATION_ROOT está set, Flask lo usará de todas formas.
            environ['SCRIPT_NAME'] = ''
            
        return self.app(environ, start_response)

application = create_app()
application.wsgi_app = CPanelMiddleware(application.wsgi_app)
