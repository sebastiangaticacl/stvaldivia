# Mejoras de Seguridad - Headers HTTP y Configuración
# Aplicar en app/__init__.py después de crear la app

import os
from flask import Flask

def setup_security_headers(app: Flask):
    """
    Configura headers de seguridad HTTP
    
    Args:
        app: Instancia de Flask
    """
    
    @app.after_request
    def set_security_headers(response):
        """Agrega headers de seguridad a todas las respuestas"""
        # Prevenir clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevenir MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Detectar entorno (DEV vs PROD)
        is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
        is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
        
        # Content Security Policy (ajustar según necesidades)
        # Self-hosted: todas las librerías están en /static/vendor/
        # Base CSP común - sin dependencias de CDNs
        script_src = "'self' 'unsafe-inline'"
        style_src = "'self' 'unsafe-inline'"
        img_src = "'self' data:"
        font_src = "'self' data:"
        
        # connect-src: diferenciar DEV vs PROD
        if is_production:
            # PRODUCCIÓN: Solo dominio real con wss (WebSocket seguro)
            connect_src = "'self' ws: wss: https://stvaldivia.cl wss://stvaldivia.cl"
        else:
            # DESARROLLO: Permitir localhost y ws/wss para desarrollo local
            connect_src = "'self' ws: wss: http://localhost:* ws://localhost:* wss://localhost:* https://stvaldivia.cl wss://stvaldivia.cl"
        
        csp = (
            f"default-src 'self'; "
            f"script-src {script_src}; "
            f"style-src {style_src}; "
            f"img-src {img_src}; "
            f"font-src {font_src}; "
            f"connect-src {connect_src}; "
            f"frame-ancestors 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Permissions Policy (antes Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=()'
        )
        
        # HSTS (solo en HTTPS, configurar en nginx para producción)
        # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app


# Uso en app/__init__.py:
"""
def create_app():
    app = Flask(__name__)
    
    # ... otras configuraciones ...
    
    # Configurar headers de seguridad
    from app.helpers.security_headers import setup_security_headers
    setup_security_headers(app)
    
    return app
"""

