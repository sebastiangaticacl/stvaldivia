"""
Middleware para comprimir respuestas HTTP (gzip)
Optimización para reducir tamaño de respuestas JSON grandes
"""
from flask import request, after_this_request
from functools import wraps
import gzip
import json


def compress_response(func):
    """
    Decorator para comprimir respuestas JSON grandes usando gzip
    Solo comprime si:
    - El cliente acepta gzip
    - La respuesta es JSON
    - El tamaño es mayor a 1KB
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        @after_this_request
        def compress(response):
            # Solo comprimir si el cliente acepta gzip
            if 'gzip' not in request.headers.get('Accept-Encoding', ''):
                return response
            
            # Solo comprimir respuestas JSON
            if response.content_type not in ['application/json', 'text/json']:
                return response
            
            # Obtener datos de la respuesta
            try:
                data = response.get_data()
                
                # Solo comprimir si es mayor a 1KB
                if len(data) < 1024:
                    return response
                
                # Comprimir con gzip
                compressed = gzip.compress(data, compresslevel=6)
                
                # Solo usar compresión si realmente reduce el tamaño
                if len(compressed) < len(data):
                    response.set_data(compressed)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = len(compressed)
                    response.headers['Vary'] = 'Accept-Encoding'
                
                return response
            except Exception:
                # Si hay error, retornar respuesta sin comprimir
                return response
        
        return func(*args, **kwargs)
    
    return wrapper

