import sys
import os
from dotenv import load_dotenv

# Project root
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)

# Load env
load_dotenv(os.path.join(project_root, '.env'))

# Force production
if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'production'

from app import create_app

application = create_app()

# WSGI Middleware to fix SCRIPT_NAME (cPanel/Passenger fix)
# Usa APPLICATION_ROOT de entorno; nunca hardcodear subpath.
class PassengerPathInfoFix(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        script_name = environ.get('SCRIPT_NAME', '')
        if not script_name or script_name == '/':
            root = (os.environ.get('APPLICATION_ROOT') or '').strip()
            if root and not root.startswith('/'):
                root = '/' + root
            if root:
                environ['SCRIPT_NAME'] = root
        return self.app(environ, start_response)

application.wsgi_app = PassengerPathInfoFix(application.wsgi_app)
