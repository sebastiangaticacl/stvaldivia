"""
WSGI entry point for Gunicorn
"""
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app

# Force configuration for subpath deployment
if 'APPLICATION_ROOT' not in os.environ:
    os.environ['APPLICATION_ROOT'] = '/stvaldivia'

if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'production'

class CPanelMiddleware(object):
    """
    Middleware para corregir problemas de ruta en cPanel/Passenger con subdirectorios.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('SCRIPT_NAME', '')
        if script_name and script_name != '/':
            environ['PATH_INFO'] = script_name + environ.get('PATH_INFO', '')
            environ['SCRIPT_NAME'] = ''
        return self.app(environ, start_response)

application = create_app()
application.wsgi_app = CPanelMiddleware(application.wsgi_app)

