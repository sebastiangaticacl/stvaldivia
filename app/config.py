"""
Configuración centralizada del sistema BIMBA.
Toda la configuración debe venir de variables de entorno.
"""
import os
from typing import Optional
from flask import Flask


class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY: str = os.environ.get('FLASK_SECRET_KEY', 'dev_key')
    
    # PHP Point of Sale API
    POS_API_URL: str = os.environ.get(
        'BASE_API_URL', 
        'https://clubbb.phppointofsale.com/index.php/api/v1'
    )
    POS_API_KEY: Optional[str] = os.environ.get('API_KEY')
    
    # Autenticación Admin
    ADMIN_PASSWORD: Optional[str] = os.environ.get('ADMIN_PASSWORD')
    ADMIN_PASSWORD_HASH: Optional[str] = os.environ.get('ADMIN_PASSWORD_HASH')
    
    # PIN del Superadmin para autorización SOS
    SUPERADMIN_PIN: str = os.environ.get('SUPERADMIN_PIN', '9999')
    
    # Rutas de archivos de persistencia (se configuran en create_app)
    LOG_FILE: Optional[str] = None
    INSTANCE_PATH: Optional[str] = None
    
    # Configuración de Antifraude (valores por defecto)
    FRAUD_MAX_HOURS_OLD_TICKET: int = 24
    FRAUD_MAX_DELIVERY_ATTEMPTS: int = 3
    
    # Configuración de Sesiones
    SESSION_TIMEOUT_MINUTES: int = 480  # 8 horas
    
    # Configuración de Cache
    CACHE_TTL_EMPLOYEES: int = 300  # 5 minutos
    CACHE_TTL_SALE_ITEMS: int = 60  # 1 minuto
    CACHE_TTL_ENTITY_DETAILS: int = 300  # 5 minutos
    
    # Configuración de Rate Limiting
    RATE_LIMIT_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOCKOUT_DURATION: int = 900  # 15 minutos
    
    # Cache-busting para CSS (actualizar cuando cambien estilos)
    CSS_VERSION: str = os.environ.get('CSS_VERSION', '20250115-01')
    
    # GETNET Serial Integration (Windows COM ports)
    ENABLE_GETNET_SERIAL: bool = os.environ.get('ENABLE_GETNET_SERIAL', '0').lower() in ('1', 'true', 'yes')
    
    # GetNet Web Checkout (para pagos online)
    GETNET_API_BASE_URL: str = os.environ.get('GETNET_API_BASE_URL', 'https://checkout.test.getnet.cl')
    GETNET_LOGIN: Optional[str] = os.environ.get('GETNET_LOGIN', '7ffbb7bf1f7361b1200b2e8d74e1d76f')  # Credenciales de prueba por defecto
    GETNET_TRANKEY: Optional[str] = os.environ.get('GETNET_TRANKEY', 'SnZP3D63n3I9dH9O')  # Credenciales de prueba por defecto
    GETNET_CLIENT_ID: Optional[str] = os.environ.get('GETNET_CLIENT_ID')  # Legacy/OAuth2
    GETNET_CLIENT_SECRET: Optional[str] = os.environ.get('GETNET_CLIENT_SECRET')  # Legacy/OAuth2
    GETNET_MERCHANT_ID: Optional[str] = os.environ.get('GETNET_MERCHANT_ID')
    GETNET_SANDBOX: bool = os.environ.get('GETNET_SANDBOX', 'true').lower() in ('1', 'true', 'yes')
    GETNET_DEMO_MODE: bool = os.environ.get('GETNET_DEMO_MODE', 'false').lower() in ('1', 'true', 'yes')  # Modo demo para desarrollo
    
    # URL pública para callbacks de GetNet (requerida porque GetNet necesita acceder desde internet)
    # En producción: https://stvaldivia.cl
    # En desarrollo local: puede usar ngrok o dejar None para usar SERVER_NAME
    PUBLIC_BASE_URL: Optional[str] = os.environ.get('PUBLIC_BASE_URL') or os.environ.get('BASE_URL')
    
    # Payment Agent API Key (para autenticación del agente local)
    AGENT_API_KEY: Optional[str] = os.environ.get('AGENT_API_KEY')
    
    # Test Registers: Mostrar cajas de prueba en selección POS
    ENABLE_TEST_REGISTERS: bool = os.environ.get('ENABLE_TEST_REGISTERS', '0').lower() in ('1', 'true', 'yes')
    
    # Configuración de OpenAI para Agente de Redes Sociales (legacy)
    OPENAI_API_KEY: Optional[str] = os.environ.get('OPENAI_API_KEY')
    OPENAI_ORGANIZATION_ID: Optional[str] = os.environ.get('OPENAI_ORGANIZATION_ID')
    OPENAI_PROJECT_ID: Optional[str] = os.environ.get('OPENAI_PROJECT_ID')
    OPENAI_DEFAULT_MODEL: str = os.environ.get('OPENAI_DEFAULT_MODEL', 'gpt-4o-mini')
    OPENAI_DEFAULT_TEMPERATURE: float = float(os.environ.get('OPENAI_DEFAULT_TEMPERATURE', '0.7'))
    
    # Configuración de Dialogflow para Agente de Redes Sociales (opcional)
    DIALOGFLOW_PROJECT_ID: Optional[str] = os.environ.get('DIALOGFLOW_PROJECT_ID')
    DIALOGFLOW_CREDENTIALS_PATH: Optional[str] = os.environ.get('DIALOGFLOW_CREDENTIALS_PATH')
    DIALOGFLOW_LANGUAGE_CODE: str = os.environ.get('DIALOGFLOW_LANGUAGE_CODE', 'es')
    # Usar Dialogflow en lugar de OpenAI (por defecto: false, usa OpenAI)
    USE_DIALOGFLOW: bool = os.environ.get('USE_DIALOGFLOW', 'false').lower() in ('1', 'true', 'yes')


def init_app_config(app: Flask):
    """
    Inicializa la configuración en la app Flask.
    Se llama desde create_app().
    """
    # Verificar si estamos en producción
    import os
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    if is_production:
        # En producción, no usar archivos locales
        app.config['INSTANCE_PATH'] = None
        app.config['LOG_FILE'] = None
    else:
        # Solo en desarrollo: configurar instance_path
        instance_path = app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        
        # Configurar rutas de archivos
        app.config['LOG_FILE'] = os.path.join(instance_path, 'logs.csv')
        app.config['INSTANCE_PATH'] = instance_path
    
    # Configuración de API
    app.config['API_KEY'] = Config.POS_API_KEY
    app.config['BASE_API_URL'] = Config.POS_API_URL
    app.config['ADMIN_PASSWORD'] = Config.ADMIN_PASSWORD
    app.config['ADMIN_PASSWORD_HASH'] = Config.ADMIN_PASSWORD_HASH
    
    # Configuración de antifraude (cargar desde archivo en desarrollo, BD en producción)
    try:
        from .helpers.fraud_config import load_fraud_config
        fraud_config = load_fraud_config()
        app.config['FRAUD_MAX_HOURS_OLD_TICKET'] = fraud_config.get(
            'max_hours_old_ticket', 
            Config.FRAUD_MAX_HOURS_OLD_TICKET
        )
        app.config['FRAUD_MAX_DELIVERY_ATTEMPTS'] = fraud_config.get(
            'max_delivery_attempts',
            Config.FRAUD_MAX_DELIVERY_ATTEMPTS
        )
    except Exception as e:
        # Si no existe, usar valores por defecto
        import logging
        logging.getLogger(__name__).warning(f"No se pudo cargar configuración de fraude: {e}")
        pass
    
    # Configuración de OpenAI
    app.config['OPENAI_API_KEY'] = Config.OPENAI_API_KEY
    app.config['OPENAI_ORGANIZATION_ID'] = Config.OPENAI_ORGANIZATION_ID
    app.config['OPENAI_PROJECT_ID'] = Config.OPENAI_PROJECT_ID
    app.config['OPENAI_DEFAULT_MODEL'] = Config.OPENAI_DEFAULT_MODEL
    app.config['OPENAI_DEFAULT_TEMPERATURE'] = Config.OPENAI_DEFAULT_TEMPERATURE
    
    # Configuración de GetNet Web Checkout
    app.config['GETNET_API_BASE_URL'] = Config.GETNET_API_BASE_URL
    app.config['GETNET_LOGIN'] = Config.GETNET_LOGIN
    app.config['GETNET_TRANKEY'] = Config.GETNET_TRANKEY
    app.config['GETNET_CLIENT_ID'] = Config.GETNET_CLIENT_ID  # Legacy/OAuth2
    app.config['GETNET_CLIENT_SECRET'] = Config.GETNET_CLIENT_SECRET  # Legacy/OAuth2
    app.config['GETNET_MERCHANT_ID'] = Config.GETNET_MERCHANT_ID
    app.config['GETNET_SANDBOX'] = Config.GETNET_SANDBOX
    app.config['GETNET_DEMO_MODE'] = Config.GETNET_DEMO_MODE
    
    # URL pública para callbacks (GetNet necesita URLs accesibles desde internet)
    app.config['PUBLIC_BASE_URL'] = Config.PUBLIC_BASE_URL
    
    # Si no hay PUBLIC_BASE_URL, intentar usar SERVER_NAME o BASE_URL
    if not app.config['PUBLIC_BASE_URL']:
        server_name = app.config.get('SERVER_NAME')
        if server_name:
            scheme = 'https' if not is_production or os.environ.get('PREFERRED_URL_SCHEME') == 'https' else 'http'
            app.config['PUBLIC_BASE_URL'] = f"{scheme}://{server_name}"
        else:
            # En desarrollo, puede necesitar ngrok o similar
            app.config['PUBLIC_BASE_URL'] = None
    
    # Logging de configuración GetNet (solo en desarrollo)
    if not is_production:
        if app.config['GETNET_CLIENT_ID']:
            app.logger.info("✅ GetNet Web Checkout configurado")
        else:
            app.logger.warning("⚠️ GetNet Web Checkout no configurado (GETNET_CLIENT_ID faltante)")

