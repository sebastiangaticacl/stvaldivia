"""
WSGI entry point for Gunicorn
"""
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'production'

from app import create_app

application = create_app()

