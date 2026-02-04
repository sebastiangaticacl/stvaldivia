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
class PassengerPathInfoFix(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        # Force SCRIPT_NAME to /stvaldivia if it's missing or root
        script_name = environ.get('SCRIPT_NAME', '')
        if not script_name or script_name == '/':
            environ['SCRIPT_NAME'] = '/stvaldivia'
        return self.app(environ, start_response)

application.wsgi_app = PassengerPathInfoFix(application.wsgi_app)
