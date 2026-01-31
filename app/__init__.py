
# BIMBA POS System - Dashboard Rewritten v4.0
import os
from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Configurar zona horaria de Chile
CHILE_TZ = pytz.timezone('America/Santiago')

# Cache thread-safe para context processor (optimización)
from .helpers.thread_safe_cache import (
    get_cached_shift_info,
    set_cached_shift_info,
    invalidate_shift_cache
)


socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    # Cargar variables de entorno
    # En producción, solo cargar desde variables de entorno del sistema, no desde archivos
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    # VALIDACIÓN CRÍTICA ANTES de crear la app Flask
    if is_production:
        secret_key = os.environ.get('FLASK_SECRET_KEY')
        if not secret_key or secret_key == 'dev_key':
            import sys
            print("❌ CRÍTICO: FLASK_SECRET_KEY debe estar configurado en producción", file=sys.stderr)
            raise ValueError("❌ CRÍTICO: FLASK_SECRET_KEY debe estar configurado en producción")
        
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            import sys
            print("❌ ERROR: DATABASE_URL no configurado en producción. La aplicación no puede funcionar sin base de datos.", file=sys.stderr)
            raise ValueError("DATABASE_URL debe estar configurado en producción. No se permite SQLite en producción.")
    
    if is_production:
        # En producción, solo usar variables de entorno del sistema
        load_dotenv()  # Cargar desde variables de entorno, no desde archivos
        env_loaded = True
    else:
        # En desarrollo: intentar cargar desde archivos .env
        env_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # Raíz del proyecto
            '/var/www/flask_app/.env',  # Servidor producción común (solo si no es Cloud Run)
            os.path.expanduser('~/.env'),  # Home del usuario
            '.env'  # Directorio actual
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                env_loaded = True
                app_logger = None
                try:
                    from flask import current_app
                    if current_app:
                        app_logger = current_app.logger
                except:
                    import logging
                    app_logger = logging.getLogger(__name__)
                if app_logger:
                    app_logger.info(f"✅ Variables de entorno cargadas desde: {env_path}")
                break
        
        # Si no se encontró ningún .env, intentar cargar desde el directorio actual
        if not env_loaded:
            load_dotenv()  # Buscar en directorio actual y padres

    app = Flask(__name__)
    
    # Configurar logging a archivo
    import logging
    from logging.handlers import RotatingFileHandler
    from datetime import datetime
    
    # Crear directorio de logs si no existe
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configurar archivo de log con rotación
    log_file = os.path.join(logs_dir, 'app.log')
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Agregar handler solo si no está en producción o si se especifica
    if not is_production or os.environ.get('ENABLE_FILE_LOGGING', '').lower() == 'true':
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info(f'✅ Logging configurado: {log_file}')
    
    # También configurar logging para GetNet específicamente
    getnet_log_file = os.path.join(logs_dir, 'getnet.log')
    getnet_handler = RotatingFileHandler(
        getnet_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    getnet_handler.setLevel(logging.INFO)
    getnet_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # Logger específico para GetNet
    getnet_logger = logging.getLogger('app.helpers.getnet_web_helper')
    if not is_production or os.environ.get('ENABLE_FILE_LOGGING', '').lower() == 'true':
        getnet_logger.addHandler(getnet_handler)
        getnet_logger.setLevel(logging.INFO)

    # Configuración - Validar ANTES de crear app si estamos en producción
    secret_key = os.environ.get('FLASK_SECRET_KEY')
    if is_production:
        if not secret_key or secret_key == 'dev_key':
            import sys
            print("❌ CRÍTICO: FLASK_SECRET_KEY debe estar configurado en producción", file=sys.stderr)
            raise ValueError("❌ CRÍTICO: FLASK_SECRET_KEY debe estar configurado en producción")
    
    if not secret_key or secret_key == 'dev_key':
        app.logger.warning("⚠️ Usando SECRET_KEY por defecto (solo desarrollo)")
    app.secret_key = secret_key or 'dev_key'
    
    # Validación de variables críticas en producción
    if is_production:
        app.logger.info("🔍 Validando variables de entorno críticas para producción...")
        
        # DATABASE_URL se valida más abajo, pero loggeamos aquí
        if not os.environ.get('DATABASE_URL'):
            app.logger.error("❌ CRÍTICO: DATABASE_URL no configurado en producción")
            # El error se lanzará más abajo, pero loggeamos aquí
        
        # Variables opcionales pero importantes
        if not os.environ.get('OPENAI_API_KEY'):
            app.logger.warning("⚠️ OPENAI_API_KEY no configurada. Bot funcionará solo con RuleEngine.")
        
        if not os.environ.get('BIMBA_INTERNAL_API_KEY'):
            app.logger.warning("⚠️ BIMBA_INTERNAL_API_KEY no configurada. API operational no funcionará.")
        
        if not os.environ.get('BIMBA_INTERNAL_API_BASE_URL'):
            app.logger.warning("⚠️ BIMBA_INTERNAL_API_BASE_URL no configurada. Bot no usará contexto operativo en producción.")
        
        app.logger.info("✅ Validación de variables de entorno completada")
    
    # Configurar CSRF Protection
    csrf = None
    try:
        from flask_wtf.csrf import CSRFProtect, CSRFError
        
        # Verificar si estamos en desarrollo (antes de inicializar CSRFProtect)
        # Verificar tanto variables de entorno como configuración de la app
        flask_env = os.environ.get('FLASK_ENV', '').lower()
        flask_debug = os.environ.get('FLASK_DEBUG', '').lower()
        
        # Si no es producción ni Cloud Run, asumimos que es desarrollo
        # Esto es más seguro: solo habilitamos CSRF en producción explícita
        is_development = not is_production and not is_cloud_run
        
        # También verificar variables de entorno explícitas
        if flask_env == 'production':
            is_development = False
        elif flask_env == 'development':
            is_development = True
        elif flask_debug == 'true':
            is_development = True
        
        csrf = CSRFProtect(app)
        
        if is_development:
            # En desarrollo: deshabilitar CSRF para facilitar testing
            app.config['WTF_CSRF_ENABLED'] = False
            app.logger.info("🔓 CSRF deshabilitado en modo desarrollo")
        else:
            # En producción: habilitar CSRF pero eximir ecommerce
            app.config['WTF_CSRF_ENABLED'] = True
            app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora
            app.config['WTF_CSRF_CHECK_DEFAULT'] = True
            app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']  # Headers para AJAX
            # Eximir rutas de ecommerce de CSRF (se manejará después de registrar blueprint)
            app.config['WTF_CSRF_EXEMPT_LIST'] = ['ecommerce.checkout', 'ecommerce.payment_callback', 'ecommerce.getnet_webhook']
        
        # Hacer csrf disponible globalmente para usar @csrf.exempt
        app.csrf = csrf
        
        # Registrar handler de errores CSRF
        @app.errorhandler(CSRFError)
        def handle_csrf_error(e):
            from flask import request, jsonify, flash, redirect, url_for
            try:
                app.logger.warning(f"⚠️ Error CSRF: {e.description}")
                
                # Si es una ruta de ecommerce, ignorar el error y permitir la petición
                if request and hasattr(request, 'path') and request.path.startswith('/ecommerce/'):
                    app.logger.info(f"⚠️ Error CSRF en ruta ecommerce ignorado: {request.path}")
                    # No hacer nada, dejar que la petición continúe
                    # Flask-WTF debería permitir la petición si la función está exenta
                    # Si no está exenta, intentar eximirla ahora
                    try:
                        # Obtener el endpoint de la ruta
                        adapter = app.url_map.bind_to_environ(request.environ)
                        endpoint, _ = adapter.match()
                        view_func = app.view_functions.get(endpoint)
                        if view_func and csrf:
                            csrf.exempt(view_func)
                            app.logger.info(f"✅ Función {endpoint} exenta de CSRF después del error")
                            # Reintentar la petición (no es posible directamente, pero al menos está exenta para la próxima)
                    except Exception as exempt_err:
                        app.logger.debug(f"No se pudo eximir función después del error: {exempt_err}")
                    
                    # Para ecommerce, simplemente no mostrar error, dejar que continúe
                    # Esto es un workaround - idealmente las funciones deberían estar exentas desde el inicio
                    return None  # Esto puede no funcionar, pero intentamos
                
                if request and hasattr(request, 'path') and request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'CSRF token missing or invalid'}), 400
                flash('Error de seguridad. Por favor, recarga la página e intenta nuevamente.', 'error')
                if request and hasattr(request, 'url'):
                    return redirect(request.url or url_for('routes.home'))
                return redirect(url_for('routes.home'))
            except Exception as err:
                app.logger.error(f"Error en handle_csrf_error: {err}")
                return redirect(url_for('routes.home'))
        
        # Context processor para csrf_token en templates (solo si CSRF está habilitado)
        @app.context_processor
        def inject_csrf_token():
            """Inyecta csrf_token en todos los templates"""
            try:
                # Solo generar token si CSRF está habilitado
                if app.config.get('WTF_CSRF_ENABLED', False):
                    from flask_wtf.csrf import generate_csrf
                    return dict(csrf_token=generate_csrf)
                else:
                    # Si CSRF está deshabilitado, retornar función dummy
                    return dict(csrf_token=lambda: '')
            except Exception as e:
                app.logger.warning(f"Error al generar CSRF token: {e}")
                return dict(csrf_token=lambda: '')
    except ImportError:
        app.logger.warning("⚠️ Flask-WTF no instalado, CSRF protection deshabilitado")
        app.config['WTF_CSRF_ENABLED'] = False
        csrf = None
        
        # Context processor dummy si no hay CSRF
        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token=lambda: '')
    # MODO SOLO LOCAL: No conectarse a servicios externos
    app.config['LOCAL_ONLY'] = os.environ.get('LOCAL_ONLY', 'true').lower() == 'true'
    if app.config['LOCAL_ONLY']:
        app.config['API_KEY'] = None  # No usar API externa
        app.config['BASE_API_URL'] = None  # No conectar a API externa
    else:
        app.config['API_KEY'] = os.environ.get('API_KEY')
        app.config['BASE_API_URL'] = os.environ.get('BASE_API_URL', "https://clubbb.phppointofsale.com/index.php/api/v1")
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD')
    app.config['ADMIN_PASSWORD_HASH'] = os.environ.get('ADMIN_PASSWORD_HASH')
    
    # Configuración Flask
    app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'development')
    app.config['FLASK_DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Debug errors mode (para captura de errores en producción si es necesario)
    app.config['DEBUG_ERRORS'] = os.environ.get('DEBUG_ERRORS', '0') == '1'
    
    # Cache-busting para CSS (actualizar cuando cambien estilos)
    app.config['CSS_VERSION'] = os.environ.get('CSS_VERSION', '20250115-01')
    
    # GETNET Serial Integration (Windows COM ports)
    app.config['ENABLE_GETNET_SERIAL'] = os.environ.get('ENABLE_GETNET_SERIAL', '0').lower() in ('1', 'true', 'yes')
    
    # GetNet Web Checkout - Configuración adicional
    app.config['GETNET_DEMO_MODE'] = os.environ.get('GETNET_DEMO_MODE', 'false').lower() in ('1', 'true', 'yes')
    
    # Payment Agent API Key
    app.config['AGENT_API_KEY'] = os.environ.get('AGENT_API_KEY')
    
    # SumUp API Configuration
    app.config['SUMUP_API_KEY'] = os.environ.get('SUMUP_API_KEY')
    app.config['SUMUP_MERCHANT_CODE'] = os.environ.get('SUMUP_MERCHANT_CODE')
    
    # Test Registers
    app.config['ENABLE_TEST_REGISTERS'] = os.environ.get('ENABLE_TEST_REGISTERS', '0').lower() in ('1', 'true', 'yes')
    
    # Configuración de zona horaria
    app.config['TIMEZONE'] = 'America/Santiago'
    app.config['CHILE_TZ'] = CHILE_TZ
    
    # Configuración SMTP para envío de emails
    app.config['SMTP_SERVER'] = os.environ.get('SMTP_SERVER')
    app.config['SMTP_PORT'] = int(os.environ.get('SMTP_PORT', '587'))
    app.config['SMTP_USER'] = os.environ.get('SMTP_USER')
    app.config['SMTP_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
    app.config['SMTP_FROM'] = os.environ.get('SMTP_FROM')
    
    
    # Configuración de OpenAI para Agente de Redes Sociales (legacy)
    # Puede configurarse independientemente del modo local
    app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
    app.config['OPENAI_ORGANIZATION_ID'] = os.environ.get('OPENAI_ORGANIZATION_ID')
    app.config['OPENAI_PROJECT_ID'] = os.environ.get('OPENAI_PROJECT_ID')
    
    # Configuración de Dialogflow para Agente de Redes Sociales (opcional)
    app.config['DIALOGFLOW_PROJECT_ID'] = os.environ.get('DIALOGFLOW_PROJECT_ID')
    app.config['DIALOGFLOW_CREDENTIALS_PATH'] = os.environ.get('DIALOGFLOW_CREDENTIALS_PATH') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    app.config['DIALOGFLOW_LANGUAGE_CODE'] = os.environ.get('DIALOGFLOW_LANGUAGE_CODE', 'es')
    # Por defecto usa OpenAI, Dialogflow solo si USE_DIALOGFLOW=true
    app.config['USE_DIALOGFLOW'] = os.environ.get('USE_DIALOGFLOW', 'false').lower() in ('1', 'true', 'yes')
    app.config['OPENAI_DEFAULT_MODEL'] = os.environ.get('OPENAI_DEFAULT_MODEL')
    app.config['OPENAI_DEFAULT_TEMPERATURE'] = float(os.environ.get('OPENAI_DEFAULT_TEMPERATURE', '0.7'))

    # Configuración de logs - ahora se guarda en base de datos
    # En producción, no usar archivos locales
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    if is_production:
        # En producción, no usar archivos locales
        app.config['INSTANCE_PATH'] = None
        app.config['LOG_FILE'] = None
        app.logger.info("✅ Modo producción: No se usarán archivos locales")
    else:
        # Solo en desarrollo: configurar instance_path
        try:
            instance_path = os.path.abspath(app.instance_path)
            os.makedirs(instance_path, exist_ok=True)
            app.config['LOG_FILE'] = os.path.join(instance_path, 'logs.csv')
            app.config['INSTANCE_PATH'] = instance_path
        except Exception as e:
            app.logger.error(f"Error al configurar instance_path: {e}", exc_info=True)
            raise

    # Configuración de base de datos para BIMBA System
    # Migrado a MySQL - soporta MySQL, PostgreSQL (legacy) y SQLite (desarrollo)
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    # Leer modo de base de datos desde variable de entorno
    # Las URLs de dev y prod deben estar en variables de entorno:
    # DATABASE_DEV_URL y DATABASE_PROD_URL
    # Ambas apuntan a bases de datos en el servidor VM
    db_mode = os.environ.get('DATABASE_MODE', 'prod')  # Por defecto producción
    
    # Obtener URL según el modo
    # IMPORTANTE: Ambas bases de datos están en el servidor VM, no localmente
    if db_mode == 'dev':
        database_url = os.environ.get('DATABASE_DEV_URL') or os.environ.get('DATABASE_URL')
        if database_url:
            app.logger.info(f"📁 Modo DESARROLLO: usando base de datos de desarrollo (servidor VM)")
    else:
        database_url = os.environ.get('DATABASE_PROD_URL') or os.environ.get('DATABASE_URL')
        if database_url:
            app.logger.info(f"📁 Modo PRODUCCIÓN: usando base de datos de producción (servidor VM)")
    
    # Si no hay URL específica, usar DATABASE_URL genérico
    if not database_url:
        database_url = os.environ.get('DATABASE_URL')
    
    # Mejorar detección DB_TYPE: reconocer mysql:// y mysql+* (cualquier mysql+*)
    db_type = None
    if database_url:
        if database_url.startswith('mysql') or 'mysql+' in database_url:
            db_type = 'mysql'
        elif database_url.startswith('postgresql') or database_url.startswith('postgres'):
            db_type = 'postgresql'
        elif database_url.startswith('sqlite'):
            db_type = 'sqlite'
        else:
            # Si no detecta tipo: en desarrollo/local asumir mysql, en producción unknown
            app.logger.warning(
                f"No se pudo detectar tipo de BD desde DATABASE_URL (formato: {database_url[:20]}...). "
                f"Asumiendo {'mysql' if not is_production else 'unknown'}."
            )
            db_type = 'mysql' if not is_production else 'unknown'
    
    if not database_url:
        if is_production:
            # Esta validación ya se hizo arriba, pero por seguridad la mantenemos
            # (no debería llegar aquí si la validación de arriba funcionó)
            import sys
            print("❌ ERROR: DATABASE_URL no configurado en producción. La aplicación no puede funcionar sin base de datos.", file=sys.stderr)
            raise ValueError("DATABASE_URL debe estar configurado en producción. No se permite SQLite en producción.")
        else:
            # Solo en desarrollo local: usar SQLite
            db_dir = instance_path
            db_path = os.path.join(db_dir, "bimba.db")
            
            # Asegurar que el directorio existe
            try:
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
            except Exception as e:
                app.logger.warning(f"⚠️ Error al preparar directorio de BD {db_dir}: {e}")
                # Fallback a /tmp solo en desarrollo
                db_dir = '/tmp'
                db_path = os.path.join(db_dir, "bimba.db")
            
            db_abs_path = os.path.abspath(db_path)
            database_url = f'sqlite:///{db_abs_path}'
            db_type = 'sqlite'
            app.logger.info(f"📁 Base de datos SQLite configurada en: {db_abs_path} (solo desarrollo local)")
    else:
        # DATABASE_URL está configurado
        if db_type == 'mysql':
            if is_production:
                app.logger.info(f"✅ Base de datos MySQL configurada para producción")
            else:
                app.logger.info(f"📁 Base de datos MySQL configurada desde DATABASE_URL (desarrollo)")
        elif db_type == 'postgresql':
            if is_production:
                app.logger.info(f"✅ Base de datos PostgreSQL configurada para producción (legacy)")
            else:
                app.logger.info(f"📁 Base de datos PostgreSQL configurada desde DATABASE_URL (desarrollo)")
        else:
            app.logger.info(f"📁 Base de datos configurada desde DATABASE_URL")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['DB_TYPE'] = db_type  # Guardar tipo de BD para uso posterior
    
    # Optimizaciones de conexión según tipo de BD
    if db_type == 'mysql':
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,  # Verificar conexiones antes de usarlas
            'pool_recycle': 3600,   # Reciclar conexiones cada hora
            'connect_args': {
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': False,
            }
        }
    elif db_type == 'postgresql':
        # Configuración legacy para PostgreSQL
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'connect_args': {
                'connect_timeout': 5,
                'options': '-c statement_timeout=10000'
            }
        }
    else:
        # SQLite - sin opciones especiales
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
        }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializar SQLAlchemy
    from .models import db
    db.init_app(app)
    
    # Después de inicializar la BD, intentar leer configuración guardada
    # Esto permite cambiar la BD dinámicamente (requiere reinicio de app)
    with app.app_context():
        try:
            from app.helpers.database_config_helper import get_database_mode, get_database_url_for_mode, set_database_urls
            
            # Leer modo guardado (si existe)
            saved_mode = get_database_mode()
            
            # Si hay URLs guardadas, usarlas
            saved_dev_url = None
            saved_prod_url = None
            try:
                from app.models.system_config_models import SystemConfig
                saved_dev_url = SystemConfig.get('database_dev_url')
                saved_prod_url = SystemConfig.get('database_prod_url')
            except:
                pass
            
            # Si hay URLs en variables de entorno, guardarlas en la BD
            env_dev_url = os.environ.get('DATABASE_DEV_URL')
            env_prod_url = os.environ.get('DATABASE_PROD_URL')
            
            if env_dev_url or env_prod_url:
                set_database_urls(
                    dev_url=env_dev_url,
                    prod_url=env_prod_url,
                    updated_by='system_init'
                )
            
            # Si el modo guardado es diferente al actual, loguear advertencia
            if saved_mode != db_mode:
                app.logger.warning(
                    f"⚠️ Modo de BD guardado ({saved_mode}) diferente al de variables de entorno ({db_mode}). "
                    f"Usando modo de variables de entorno. Para cambiar, usa el panel de control."
                )
        except Exception as e:
            # Si falla (primera vez, BD no disponible, etc.), continuar con configuración actual
            app.logger.debug(f"No se pudo leer configuración de BD guardada: {e}")

    # Logging de configuración cargada (después de crear la app)
    if not is_production:
        env_path_used = None
        for env_path in env_paths:
            if os.path.exists(env_path):
                env_path_used = env_path
                break
        
        if env_path_used:
            app.logger.info(f"✅ Variables de entorno cargadas desde: {env_path_used}")
            app.logger.info(f"   API_KEY configurada: {'Sí' if os.environ.get('API_KEY') else 'No'}")
            app.logger.info(f"   BASE_API_URL configurada: {'Sí' if os.environ.get('BASE_API_URL') else 'No'}")
        else:
            app.logger.warning("⚠️  No se encontró archivo .env en ubicaciones estándar")
    else:
        app.logger.info("✅ Variables de entorno cargadas desde variables de entorno del sistema (producción)")
        app.logger.info(f"   API_KEY configurada: {'Sí' if os.environ.get('API_KEY') else 'No'}")
        app.logger.info(f"   BASE_API_URL configurada: {'Sí' if os.environ.get('BASE_API_URL') else 'No'}")
        app.logger.info(f"   API_KEY en env: {'Sí' if os.environ.get('API_KEY') else 'No'}")
        app.logger.info(f"   BASE_API_URL en env: {'Sí' if os.environ.get('BASE_API_URL') else 'No'}")

    # Inicializar SocketIO con configuración para sesiones
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        manage_session=True,  # Permitir que SocketIO gestione sesiones
        logger=True,
        engineio_logger=False
    )

    # Obtener prefijo de URL de variables de entorno
    url_prefix = os.environ.get('APPLICATION_ROOT', '')
    
    # Registrar blueprint de home (ruta raíz)
    from .routes.home_routes import home_bp
    app.register_blueprint(home_bp, url_prefix=url_prefix)
    
    # Registrar blueprint de autenticación
    from .routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix=url_prefix)
    
    # Exempt login_admin de CSRF después de registrar el blueprint (se maneja con rate limiting)
    if csrf and hasattr(auth_bp, 'view_functions') and 'login_admin' in auth_bp.view_functions:
        csrf.exempt(auth_bp.view_functions['login_admin'])
    
    # Registrar rutas
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp, url_prefix=url_prefix)
    
    # Registrar blueprint de WhatsApp
    try:
        from .routes.whatsapp_routes import whatsapp_bp
        app.register_blueprint(whatsapp_bp)
        app.logger.info("✅ Blueprint de WhatsApp registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de WhatsApp: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de WhatsApp: {e}")
    
    # Blueprint de auditoría de caja SUPERADMIN
    try:
        from app.routes_superadmin_audit import superadmin_audit_bp
        app.register_blueprint(superadmin_audit_bp, url_prefix=url_prefix)
        app.logger.info("✅ Blueprint de auditoría SUPERADMIN registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de auditoría SUPERADMIN: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de auditoría SUPERADMIN: {e}")
    
    # Registrar blueprint de productos
    try:
        from app.routes.product_routes import product_bp
        app.register_blueprint(product_bp)
        app.logger.info("✅ Blueprint de productos registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de productos: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de productos: {e}")
    
    # Registrar blueprint de ingredientes
    try:
        from app.routes.ingredient_routes import ingredient_bp
        app.register_blueprint(ingredient_bp)
        app.logger.info("✅ Blueprint de ingredientes registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de ingredientes: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de ingredientes: {e}")
    
    # Registrar blueprint de administración de inventario mejorado
    try:
        from app.routes.inventory_admin_routes import inventory_admin_bp
        app.register_blueprint(inventory_admin_bp)
        app.logger.info("✅ Blueprint de administración de inventario registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de administración de inventario: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de administración de inventario: {e}")
    
    # Registrar blueprint de administración de cajas (independiente de inventario)
    try:
        from app.routes.register_admin_routes import register_admin_bp
        app.register_blueprint(register_admin_bp)
        app.logger.info("✅ Blueprint de administración de cajas registrado")
        
        # Registrar blueprint de dashboard de TPV
        try:
            from app.routes.tpv_dashboard_routes import tpv_dashboard_bp
            app.register_blueprint(tpv_dashboard_bp)
            app.logger.info("✅ Blueprint de dashboard de TPV registrado")
        except ImportError as e:
            app.logger.warning(f"⚠️  No se pudo registrar el blueprint de dashboard de TPV: {e}")
        except Exception as e:
            app.logger.error(f"❌ Error al registrar blueprint de dashboard de TPV: {e}")
    except ImportError as e:
        app.logger.error(f"❌ Error al registrar blueprint de administración de cajas: {e}")
    except Exception as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de administración de cajas: {e}")
    
    # Registrar blueprint de recetas (API)
    try:
        from app.routes.recipe_routes import recipe_bp
        app.register_blueprint(recipe_bp)
        app.logger.info("✅ Blueprint de recetas (API) registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de recetas: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de recetas: {e}")
    
    # Registrar blueprint de encuestas
    # El blueprint ya tiene url_prefix='/encuesta' definido
    # Si APPLICATION_ROOT está configurado, combinarlo con el prefijo del blueprint
    from .survey import survey_bp
    if url_prefix:
        # Combinar APPLICATION_ROOT con el prefijo del blueprint
        combined_prefix = f"{url_prefix}/encuesta" if not url_prefix.endswith('/') else f"{url_prefix}encuesta"
        app.register_blueprint(survey_bp, url_prefix=combined_prefix)
    else:
        # Usar solo el url_prefix del blueprint (/encuesta)
        app.register_blueprint(survey_bp)
    
    # Registrar blueprint de equipo
    from .blueprints.equipo import equipo_bp
    if url_prefix:
        combined_prefix = f"{url_prefix}/admin/equipo" if not url_prefix.endswith('/') else f"{url_prefix}admin/equipo"
        app.register_blueprint(equipo_bp, url_prefix=combined_prefix)
    else:
        app.register_blueprint(equipo_bp)
    
    # Eximir APIs de equipo de CSRF si está habilitado
    if csrf:
        try:
            # Eximir solo las rutas API
            csrf.exempt(equipo_bp)
        except:
            pass
    
    # Registrar blueprint de guardarropía (para trabajadores - sin /admin)
    from .blueprints.guardarropia import guardarropia_bp, guardarropia_admin_bp
    if url_prefix:
        # Blueprint principal para trabajadores
        combined_prefix = f"{url_prefix}/guardarropia" if not url_prefix.endswith('/') else f"{url_prefix}guardarropia"
        app.register_blueprint(guardarropia_bp, url_prefix=combined_prefix)
        # Blueprint administrativo
        combined_prefix_admin = f"{url_prefix}/admin/guardarropia" if not url_prefix.endswith('/') else f"{url_prefix}admin/guardarropia"
        app.register_blueprint(guardarropia_admin_bp, url_prefix=combined_prefix_admin)
    else:
        app.register_blueprint(guardarropia_bp)
        app.register_blueprint(guardarropia_admin_bp)
    
    # Registrar blueprint de admin para Bot de IA
    from .blueprints.admin import admin_bp
    if url_prefix:
        combined_prefix = f"{url_prefix}/admin" if not url_prefix.endswith('/') else f"{url_prefix}admin"
        app.register_blueprint(admin_bp, url_prefix=combined_prefix)
    else:
        app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Eximir blueprint de admin de CSRF si está habilitado (usa autenticación de sesión)
    if csrf:
        try:
            csrf.exempt(admin_bp)
        except:
            pass
    
    app.logger.info("✅ Blueprint de admin (Bot de IA) registrado")
    
    # Eximir APIs de guardarropía de CSRF si está habilitado
    if csrf:
        try:
            csrf.exempt(guardarropia_bp)
        except:
            pass
    
    app.logger.info("✅ Blueprint de guardarropía registrado (trabajadores y admin)")
    
    # Registrar blueprint de notificaciones
    from .blueprints.notifications import bp as notifications_bp
    app.register_blueprint(notifications_bp)
    
    # Eximir APIs de notificaciones de CSRF si está habilitado
    if csrf:
        try:
            csrf.exempt(notifications_bp)
        except:
            pass
    
    app.logger.info("✅ Blueprint de notificaciones registrado")
    
    # Registrar blueprint de API
    try:
        from .routes.api_routes import api_bp
        # El blueprint ya tiene url_prefix='/api', no sobrescribir
        app.register_blueprint(api_bp)
        
        # Eximir APIs de CSRF si está habilitado
    except Exception as e:
        app.logger.warning(f"No se pudo registrar api_bp: {e}")
    
    # Registrar blueprint de API BIMBA
    try:
        from .routes.api_bimba import bp as api_bimba_bp
        app.register_blueprint(api_bimba_bp)
        
        # Eximir APIs de BIMBA de CSRF si está habilitado
        if csrf:
            try:
                csrf.exempt(api_bimba_bp)
            except:
                pass
        
        app.logger.info("✅ Blueprint de API BIMBA registrado")
    except Exception as e:
        app.logger.warning(f"No se pudo registrar api_bimba_bp: {e}")
    
    # Registrar blueprint de API V1
    try:
        from .blueprints.api.api_v1 import api_v1
        app.register_blueprint(api_v1)
        
        # Eximir API V1 de CSRF si está habilitado
        if csrf:
            try:
                csrf.exempt(api_v1)
            except:
                pass
        
        app.logger.info("✅ Blueprint de API V1 registrado")
    except Exception as e:
        app.logger.warning(f"No se pudo registrar api_v1: {e}")
    
    # Registrar blueprint de API Operational
    try:
        from .blueprints.api.api_operational import operational_api
        app.register_blueprint(operational_api)
        
        # Eximir API Operational de CSRF si está habilitado
        if csrf:
            try:
                csrf.exempt(operational_api)
            except:
                pass
        
        app.logger.info("✅ Blueprint de API Operational registrado")
    except Exception as e:
        app.logger.warning(f"No se pudo registrar operational_api: {e}")
        if csrf:
            csrf.exempt(api_bp)
        
        app.logger.info("✅ Blueprint de API registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de API: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de API: {e}")
    
    # Registrar blueprint de n8n webhooks
    try:
        from .routes.n8n_routes import n8n_bp
        app.register_blueprint(n8n_bp)
        
        # Eximir APIs de n8n de CSRF si está habilitado (webhooks externos)
        if csrf:
            try:
                csrf.exempt(n8n_bp)
            except:
                pass
        
        app.logger.info("✅ Blueprint de n8n registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de n8n: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de n8n: {e}")
    
    # Registrar blueprint de Instagram webhooks
    try:
        from .routes_instagram import instagram_bp
        app.register_blueprint(instagram_bp, url_prefix=url_prefix)
        app.logger.info("✅ Blueprint de Instagram registrado")
    except ImportError:
        # Si no existe el módulo, continuar sin errores (opcional)
        pass
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de Instagram: {e}")
    
    # Registrar blueprint de Facebook webhooks
    try:
        from .routes.facebook_routes import facebook_bp
        app.register_blueprint(facebook_bp, url_prefix=url_prefix)
        app.logger.info("✅ Blueprint de Facebook registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de Facebook: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de Facebook: {e}")
    except ImportError:
        # Si no existe el módulo, continuar sin errores (opcional)
        pass
    
    # Configuración Kiosko
    app.config['KIOSK_ENABLED'] = os.environ.get('KIOSK_ENABLED', 'true').lower() == 'true'
    
    # Registrar blueprint de Kiosko
    # Crear tablas de la base de datos si no existen (siempre, no solo para kiosko)
    with app.app_context():
        try:
            # Intentar crear tablas con manejo mejorado de errores
            db.create_all()
            app.logger.info("✅ Base de datos inicializada (todas las tablas)")
        except Exception as e:
            app.logger.error(f"❌ Error al inicializar base de datos: {e}", exc_info=True)
            # No fallar completamente si hay error en la BD - la app puede funcionar sin BD inicialmente
            app.logger.warning("⚠️ Continuando sin inicializar base de datos (puede causar errores en funcionalidades que la requieren)")
    
    if app.config['KIOSK_ENABLED']:
        try:
            from .blueprints.kiosk import kiosk_bp
            # El blueprint ya tiene url_prefix='/kiosk', solo agregar APPLICATION_ROOT si existe
            if url_prefix:
                combined_prefix = f"{url_prefix}/kiosk" if not url_prefix.endswith('/') else f"{url_prefix}kiosk"
                app.register_blueprint(kiosk_bp, url_prefix=combined_prefix)
            else:
                app.register_blueprint(kiosk_bp)
            
            # Eximir blueprint de kiosko de CSRF si está habilitado (APIs públicas)
            if csrf:
                try:
                    csrf.exempt(kiosk_bp)
                    app.logger.info("✅ Blueprint de kiosko exento de CSRF")
                except Exception as exempt_error:
                    app.logger.debug(f"No se pudo eximir blueprint de kiosko de CSRF: {exempt_error}")
        except ImportError as e:
            app.logger.warning(f"⚠️  No se pudo registrar el blueprint del kiosko: {e}")
        except Exception as e:
            app.logger.error(f"❌ Error al registrar blueprint del kiosko: {e}")
    else:
        app.logger.info("⚠️  Kiosko desactivado")
    
    # Registrar blueprint de scanner (barra/bartender)
    try:
        from .routes.scanner_routes import scanner_bp
        app.register_blueprint(scanner_bp, url_prefix=url_prefix)
        app.logger.info("✅ Blueprint de scanner (barra/bartender) registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de scanner: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de scanner: {e}")
    
    # Registrar blueprint de turnos de bartender
    try:
        from app.blueprints.bartender_turnos.routes import bartender_turnos_bp
        app.register_blueprint(bartender_turnos_bp)
        app.logger.info("✅ Blueprint de turnos de bartender registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de turnos de bartender: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de turnos de bartender: {e}")
    
    # Registrar filtros de template personalizados
    from app.helpers.template_filters import format_datetime, format_date, format_time
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_time'] = format_time
    
    # Context processor para verificar si estamos en producción
    @app.context_processor
    def inject_production_check():
        try:
            is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
            is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
            return {
                'is_production': is_production,
                'is_cloud_run': is_cloud_run
            }
        except Exception as e:
            # En caso de error, retornar valores por defecto seguros
            try:
                app.logger.warning(f"Error en inject_production_check: {e}")
            except:
                pass
            return {
                'is_production': False,
                'is_cloud_run': False
            }
    
        # Registrar blueprint de Ecommerce (Venta de Entradas)
    try:
        from .blueprints.ecommerce import ecommerce_bp
        if url_prefix:
            combined_prefix = f"{url_prefix}/ecommerce" if not url_prefix.endswith('/') else f"{url_prefix}ecommerce"
            app.register_blueprint(ecommerce_bp, url_prefix=combined_prefix)
        else:
            app.register_blueprint(ecommerce_bp)
        
        # Eximir callbacks de GetNet de CSRF (vienen desde GetNet, no pueden incluir token)
        # También eximir checkout POST temporalmente para evitar problemas de CSRF
        if csrf:
            try:
                # Método 1: Eximir todo el blueprint de ecommerce de CSRF
                csrf.exempt(ecommerce_bp)
                app.logger.info("⚠️ Blueprint ecommerce exento de CSRF (nivel blueprint)")
                
                # Método 2: También eximir las funciones específicas (incluyendo las marcadas con decorador)
                if hasattr(ecommerce_bp, 'view_functions'):
                    exempted_count = 0
                    for func_name, view_func in ecommerce_bp.view_functions.items():
                        try:
                            # Eximir si está marcada con decorador o siempre
                            if getattr(view_func, '_csrf_exempt', False) or True:  # Siempre eximir para ecommerce
                                csrf.exempt(view_func)
                                exempted_count += 1
                        except Exception as func_exempt_error:
                            app.logger.debug(f"No se pudo eximir función {func_name}: {func_exempt_error}")
                    app.logger.info(f"⚠️ {exempted_count} funciones de ecommerce exentas de CSRF (nivel función)")
                    
            except Exception as exempt_error:
                app.logger.error(f"❌ No se pudo eximir blueprint de CSRF: {exempt_error}", exc_info=True)
        
        app.logger.info("✅ Blueprint de Ecommerce registrado")
        
        # Registrar blueprint de admin ecommerce
        try:
            from .blueprints.ecommerce.admin_routes import admin_ecommerce_bp
            app.register_blueprint(admin_ecommerce_bp)
            app.logger.info("✅ Blueprint de Admin Ecommerce registrado")
        except ImportError as e:
            app.logger.warning(f"⚠️  No se pudo registrar el blueprint de admin ecommerce: {e}")
        except Exception as e:
            app.logger.error(f"❌ Error al registrar blueprint de admin ecommerce: {e}")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de ecommerce: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de ecommerce: {e}")
    
    # Registrar blueprint de Caja (POS)
    try:
        from .blueprints.pos import caja_bp
        # El blueprint ya tiene url_prefix='/caja' definido
        # Si APPLICATION_ROOT está configurado y no está vacío, combinarlo con el prefijo del blueprint
        if url_prefix and url_prefix.strip() and url_prefix != '/':
            # Combinar APPLICATION_ROOT con el prefijo del blueprint
            # El blueprint tiene url_prefix='/caja', así que combinamos
            if url_prefix.endswith('/'):
                combined_prefix = f"{url_prefix.rstrip('/')}/caja"
            else:
                combined_prefix = f"{url_prefix}/caja"
            # IMPORTANTE: pasar url_prefix=None para que use el del blueprint, luego combinamos
            # En realidad, Flask combina automáticamente, así que solo pasamos el combined_prefix
            app.register_blueprint(caja_bp, url_prefix=combined_prefix)
            app.logger.info(f"✅ Blueprint de Caja registrado con prefijo: {combined_prefix}")
        else:
            # Usar solo el url_prefix del blueprint (/caja)
            # No pasar url_prefix para que use el del blueprint
            app.register_blueprint(caja_bp)
            app.logger.info("✅ Blueprint de Caja registrado con prefijo: /caja (del blueprint)")
        
        # Verificar que las rutas están registradas (después de que la app esté completamente inicializada)
        # Esto se hace en un contexto de aplicación para asegurar que las rutas estén disponibles
        def verify_routes():
            try:
                login_routes = []
                for rule in app.url_map.iter_rules():
                    if 'login' in rule.rule.lower() and 'caja' in rule.rule.lower():
                        login_routes.append(rule.rule)
                if login_routes:
                    app.logger.info(f"   ✅ Rutas de login encontradas: {', '.join(login_routes)}")
                else:
                    app.logger.warning("   ⚠️ Rutas de login NO encontradas en el mapa de URLs")
                    # Listar todas las rutas de caja para debugging
                    caja_routes = [rule.rule for rule in app.url_map.iter_rules() if 'caja' in rule.rule.lower()]
                    if caja_routes:
                        app.logger.info(f"   Rutas de caja disponibles: {', '.join(caja_routes[:10])}")
            except Exception as e:
                app.logger.debug(f"No se pudo verificar rutas (normal durante inicialización): {e}")
        
        # Verificar después de que todos los blueprints estén registrados
        app.after_request_funcs.setdefault(None, []).append(lambda response: verify_routes() or response)
        
        # Eximir APIs de POS de CSRF si está habilitado
        if csrf:
            try:
                csrf.exempt(caja_bp)
            except:
                pass
    except ImportError as e:
        app.logger.error(f"❌ No se pudo importar el blueprint de caja: {e}", exc_info=True)
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de caja: {e}", exc_info=True)
    
    # Error handler global para capturar errores 500 (solo loguea, no maneja)
    # El manejo real se hace en error_handlers.py si está registrado
    # Este handler solo asegura que los errores se logueen correctamente
    @app.errorhandler(500)
    def handle_500_error(e):
        # Solo loguear el error, no manejarlo
        # Dejar que Flask o el handler en error_handlers.py lo maneje
        try:
            from flask import current_app
            current_app.logger.error(f"❌ Error 500 capturado: {str(e)}", exc_info=True)
        except:
            try:
                import logging
                logging.error(f"Error 500: {str(e)}", exc_info=True)
            except:
                pass
        # Re-lanzar el error para que Flask o el handler en error_handlers.py lo maneje
        # Si no hay otro handler, Flask mostrará su página de error por defecto
        raise
    
    # Context processor para obtener estado de puntos de venta TPV
    @app.context_processor
    def inject_tpv_status():
        """Inyecta el estado de los puntos de venta (Cajas, Kioskos, Ecommerce) en todos los templates"""
        tpv_status = {
            'cajas': {'total': 0, 'abiertas': 0, 'cerradas': 0},
            'kioskos': {'total': 1, 'activos': 1, 'inactivos': 0},  # Por defecto 1 kiosko activo
            'ecommerce': {'total': 1, 'activo': True}  # Por defecto activo
        }
        
        try:
            from app.helpers.register_lock_db import get_all_register_locks
            from app.blueprints.pos.services import pos_service
            
            # Obtener estado de cajas
            try:
                # Obtener cajas desde API o usar por defecto
                default_registers = 6
                try:
                    api_registers = pos_service.get_registers()
                    if api_registers and len(api_registers) > 0:
                        total_cajas = len(api_registers)
                    else:
                        total_cajas = default_registers
                except:
                    total_cajas = default_registers
                
                # Obtener cajas abiertas (con bloqueos activos)
                register_locks = get_all_register_locks()
                cajas_abiertas = len(register_locks)
                
                tpv_status['cajas'] = {
                    'total': total_cajas,
                    'abiertas': cajas_abiertas,
                    'cerradas': total_cajas - cajas_abiertas
                }
            except Exception as e:
                current_app.logger.warning(f"Error al obtener estado de cajas: {e}")
                tpv_status['cajas'] = {'total': 6, 'abiertas': 0, 'cerradas': 6}
            
            # Estado de kioskos (por ahora asumimos que está activo si está habilitado)
            try:
                from flask import current_app
                kiosk_enabled = current_app.config.get('KIOSK_ENABLED', True)
                tpv_status['kioskos'] = {
                    'total': 1,
                    'activos': 1 if kiosk_enabled else 0,
                    'inactivos': 0 if kiosk_enabled else 1
                }
            except:
                tpv_status['kioskos'] = {'total': 1, 'activos': 1, 'inactivos': 0}
            
            # Estado de ecommerce (por ahora siempre activo)
            tpv_status['ecommerce'] = {'total': 1, 'activo': True}
            
        except Exception as e:
            try:
                current_app.logger.warning(f"Error al obtener estado TPV: {e}")
            except:
                pass
        
        return {'tpv_status': tpv_status}
    
    # Context processor para hacer shift_status y shift_metrics disponibles en todos los templates
    @app.context_processor
    def inject_shift_info():
        """Inyecta información del turno en todos los templates para el footer general (sistema único - Jornada)"""
        # Valores por defecto seguros que siempre se retornan
        default_result = {
            'global_shift_status': {'is_open': False},
            'global_shift_metrics': {},
            'shift_status': {'is_open': False},
            'shift_metrics': {},
            'app_version': 'N/A',
            'app_version_full': 'N/A',
            'app_build_info': {}
        }
        
        # Inyectar información de versión de forma segura
        try:
            from .helpers.version import get_version_string, get_full_version_string, get_build_info
            version_info = {
                'app_version': get_version_string(),
                'app_version_full': get_full_version_string(),
                'app_build_info': get_build_info()
            }
        except Exception:
            version_info = default_result.copy()
        
        # Intentar obtener desde caché primero
        try:
            cached_info = get_cached_shift_info()
            if cached_info:
                return {
                    **cached_info,
                    **version_info
                }
        except Exception:
            pass
        
        # Si hay cualquier error, retornar valores por defecto
        try:
            from .application.services.service_factory import get_stats_service
            from datetime import datetime
            import pytz
            from .models.jornada_models import Jornada
            from sqlalchemy.exc import OperationalError, DisconnectionError
            
            # Usar solo sistema de Jornadas (sistema único)
            from flask import current_app
            # Importar CHILE_TZ desde módulo único de timezone
            try:
                from app.utils.timezone import CHILE_TZ
            except ImportError:
                # Fallback: usar timezone_utils si existe
                try:
                    from app.helpers.timezone_utils import CHILE_TZ
                except ImportError:
                    try:
                        current_app.logger.error("No se pudo importar CHILE_TZ desde ningún módulo")
                    except:
                        pass
                    CHILE_TZ = None
            
            try:
                fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d') if CHILE_TZ else datetime.utcnow().strftime('%Y-%m-%d')
            except Exception as date_error:
                try:
                    current_app.logger.warning(f"Error al obtener fecha_hoy en context processor: {date_error}")
                except:
                    pass
                fecha_hoy = datetime.utcnow().strftime('%Y-%m-%d')
            
            # Intentar consultar jornada, pero manejar errores de conexión a BD
            jornada_abierta = None
            try:
                jornada_abierta = Jornada.query.filter_by(
                    fecha_jornada=fecha_hoy,
                    estado_apertura='abierto'
                ).first()
            except (OperationalError, DisconnectionError) as db_error:
                # Error de conexión a BD - continuar sin BD
                try:
                    current_app.logger.warning(f"BD no disponible en context processor (continuando sin BD): {db_error}")
                except:
                    pass
                jornada_abierta = None
            except Exception as query_error:
                # Otro tipo de error en el query
                try:
                    current_app.logger.warning(f"Error al consultar jornada en context processor: {query_error}")
                except:
                    pass
                jornada_abierta = None
            
            # Si hay jornada abierta, usar esa información
            if jornada_abierta:
                try:
                    opened_at_value = None
                    if jornada_abierta.abierto_en:
                        if hasattr(jornada_abierta.abierto_en, 'isoformat'):
                            opened_at_value = jornada_abierta.abierto_en.isoformat()
                        else:
                            opened_at_value = str(jornada_abierta.abierto_en)
                    if not opened_at_value:
                        opened_at_value = jornada_abierta.horario_apertura_programado or None
                    
                    shift_status_dict = {
                        'is_open': True,
                        'shift_date': jornada_abierta.fecha_jornada or fecha_hoy,
                        'opened_at': opened_at_value,
                        'closed_at': None,
                        'fiesta_nombre': jornada_abierta.nombre_fiesta or None,
                        'djs': jornada_abierta.djs or None
                    }
                except Exception as attr_error:
                    try:
                        current_app.logger.warning(f"Error al acceder a atributos de jornada en context processor: {attr_error}")
                    except:
                        pass
                    shift_status_dict = {
                        'is_open': False,
                        'shift_date': fecha_hoy,
                        'opened_at': None,
                        'closed_at': None,
                        'fiesta_nombre': None,
                        'djs': None
                    }
            else:
                shift_status_dict = {
                    'is_open': False,
                    'shift_date': fecha_hoy,
                    'opened_at': None,
                    'closed_at': None,
                    'fiesta_nombre': None,
                    'djs': None
                }
            
            shift_metrics = {}
            if shift_status_dict.get('is_open', False):
                try:
                    stats_service = get_stats_service()
                    
                    # Calcular tiempo transcurrido
                    opened_at_str = shift_status_dict.get('opened_at')
                    if opened_at_str:
                        try:
                            opened_dt = datetime.fromisoformat(opened_at_str.replace('Z', '+00:00') if 'Z' in opened_at_str else opened_at_str)
                            now = datetime.utcnow()
                            diff = now - opened_dt
                            hours = int(diff.total_seconds() // 3600)
                            minutes = int((diff.total_seconds() % 3600) // 60)
                            shift_metrics['tiempo_transcurrido'] = f"{hours}h {minutes}m"
                        except:
                            shift_metrics['tiempo_transcurrido'] = 'N/A'
                    else:
                        shift_metrics['tiempo_transcurrido'] = 'N/A'
                    
                    # Obtener estadísticas del turno
                    try:
                        shift_date = shift_status_dict.get('shift_date', fecha_hoy)
                        delivery_stats = stats_service.get_delivery_stats(
                            start_date=shift_date,
                            end_date=shift_date
                        )
                        shift_metrics['total_entregas'] = delivery_stats.get('total_deliveries', 0)
                    except Exception as stats_error:
                        try:
                            current_app.logger.warning(f"Error al obtener estadísticas en context processor: {stats_error}")
                        except:
                            pass
                        shift_metrics['total_entregas'] = 0
                    
                    # Obtener entradas - OPTIMIZADO: No llamar a API externa en cada request
                    # Esto causaba lentitud extrema en login y navegación
                    # Se debe cargar asíncronamente o usar un valor en caché
                    shift_metrics['total_entradas'] = 0 # Placeholder para evitar bloqueo
                    
                    # TODO: Implementar carga asíncrona de entradas si es necesario
                    # from .helpers.pos_api import get_entradas_sales
                    # try:
                    #     entradas_sales = get_entradas_sales(limit=100)
                    #     shift_metrics['total_entradas'] = len([s for s in entradas_sales if s.get('sale_time', '').startswith(shift_date)])
                    # except:
                    #     shift_metrics['total_entradas'] = 0
                except Exception as e:
                    try:
                        from flask import current_app
                        current_app.logger.warning(f"Error al calcular métricas del turno en context processor: {e}")
                    except:
                        pass
                    shift_metrics = {
                        'tiempo_transcurrido': 'N/A',
                        'total_entregas': 0,
                        'total_entradas': 0
                    }
            
            # Guardar en caché
            result = {
                'global_shift_status': shift_status_dict,
                'global_shift_metrics': shift_metrics,
                'shift_status': shift_status_dict,  # Compatibilidad
                'shift_metrics': shift_metrics,  # Compatibilidad
                **version_info
            }
            set_cached_shift_info(result)
            return result
        except Exception as e:
            # En caso de cualquier error, retornar valores por defecto seguros
            # NO intentar loguear si hay problemas con current_app
            try:
                from flask import current_app
                try:
                    current_app.logger.error(f"Error en context processor de shift_info: {e}", exc_info=True)
                except:
                    pass
            except:
                try:
                    import logging
                    logging.error(f"Error en context processor de shift_info: {e}", exc_info=True)
                except:
                    pass
            # Siempre retornar valores por defecto seguros
            return {
                'global_shift_status': {'is_open': False},
                'global_shift_metrics': {},
                'shift_status': {'is_open': False},
                'shift_metrics': {},
                'app_version': version_info.get('app_version', 'N/A'),
                'app_version_full': version_info.get('app_version_full', 'N/A'),
                'app_build_info': version_info.get('app_build_info', {})
            }

    # Registrar eventos de socket
    from .socketio_events import register_socketio_events
    register_socketio_events(socketio)
    
    # Inicializar thread de métricas periódicas después de registrar eventos
    if hasattr(socketio, '_start_metrics_thread'):
        socketio._start_metrics_thread(app)
        app.logger.info("✅ Thread de métricas periódicas iniciado")
    
    # Configuración de Instagram/Meta Webhooks
    app.config['INSTAGRAM_VERIFY_TOKEN'] = os.environ.get('INSTAGRAM_VERIFY_TOKEN')
    app.config['INSTAGRAM_PAGE_ACCESS_TOKEN'] = os.environ.get('INSTAGRAM_PAGE_ACCESS_TOKEN')
    app.config['INSTAGRAM_BUSINESS_ACCOUNT_ID'] = os.environ.get('INSTAGRAM_BUSINESS_ACCOUNT_ID')
    app.config['META_APP_ID'] = os.environ.get('META_APP_ID')
    app.config['META_APP_SECRET'] = os.environ.get('META_APP_SECRET')
    
    # Configuración de n8n Integration
    # Se leerá desde SystemConfig en tiempo de ejecución, pero inicializar con variables de entorno
    app.config['N8N_WEBHOOK_URL'] = os.environ.get('N8N_WEBHOOK_URL')
    app.config['N8N_WEBHOOK_SECRET'] = os.environ.get('N8N_WEBHOOK_SECRET')
    app.config['N8N_API_KEY'] = os.environ.get('N8N_API_KEY')
    
    # Actualizar desde SystemConfig si existe (después de inicializar la BD)
    with app.app_context():
        try:
            from app.models.system_config_models import SystemConfig
            n8n_webhook_url = SystemConfig.get('n8n_webhook_url')
            n8n_webhook_secret = SystemConfig.get('n8n_webhook_secret')
            n8n_api_key = SystemConfig.get('n8n_api_key')
            
            if n8n_webhook_url:
                app.config['N8N_WEBHOOK_URL'] = n8n_webhook_url
            if n8n_webhook_secret:
                app.config['N8N_WEBHOOK_SECRET'] = n8n_webhook_secret
            if n8n_api_key:
                app.config['N8N_API_KEY'] = n8n_api_key
        except Exception as e:
            app.logger.debug(f"No se pudo leer configuración n8n desde SystemConfig: {e}")

    # Registrar filtros personalizados de Jinja2
    @app.template_filter('to_datetime')
    def to_datetime_filter(value):
        """Convierte un string de fecha a objeto datetime"""
        if not value or not isinstance(value, str):
            return None
        try:
            # Intentar diferentes formatos comunes
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Formatea un número como moneda chilena: puntos como separador de miles, sin decimales"""
        if value is None:
            return '0'
        try:
            # Convertir a float y redondear a entero
            num = int(round(float(value)))
            # Formatear con puntos como separador de miles (formato chileno)
            return f'{num:,}'.replace(',', '.')
        except (ValueError, TypeError):
            return '0'
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parsea un string JSON a diccionario"""
        if not value:
            return {}
        try:
            import json
            return json.loads(value)
        except:
            return {}
    
    @app.template_filter('fecha')
    def fecha_filter(value):
        """Formatea una fecha en formato día/mes/año hora:minuto (24 horas)"""
        if value is None:
            return 'N/A'
        
        try:
            # Si ya es un string con formato conocido, intentar parsearlo
            if isinstance(value, str):
                # Intentar diferentes formatos comunes
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%d',
                    '%d-%m-%Y, %I:%M %p',  # Formato que ya tenemos en algunos lugares
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M',
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        # Formato: DD/MM/YYYY HH:MM
                        return dt.strftime('%d/%m/%Y %H:%M')
                    except ValueError:
                        continue
                
                # Si no coincide con ningún formato, retornar el valor original
                return value
            
            # Si es un objeto datetime
            elif isinstance(value, datetime):
                return value.strftime('%d/%m/%Y %H:%M')
            
            return str(value)
            
        except Exception as e:
            # Si hay algún error, retornar el valor original o 'N/A'
            return str(value) if value else 'N/A'
    
    @app.template_filter('fecha_solo')
    def fecha_solo_filter(value):
        """Formatea una fecha en formato día/mes/año (sin hora)"""
        if value is None:
            return 'N/A'
        
        try:
            if isinstance(value, str):
                # Intentar diferentes formatos
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%Y-%m-%dT%H:%M:%S',
                    '%d/%m/%Y',
                    '%d-%m-%Y',
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value.split()[0] if ' ' in value else value, fmt.split()[0] if ' ' in fmt else fmt)
                        return dt.strftime('%d/%m/%Y')
                    except (ValueError, IndexError):
                        continue
                
                return value.split()[0] if ' ' in value else value
            
            elif isinstance(value, datetime):
                return value.strftime('%d/%m/%Y')
            
            return str(value)
            
        except Exception:
            return str(value) if value else 'N/A'
    
    @app.template_filter('hora')
    def hora_filter(value):
        """Formatea solo la hora en formato 24 horas (HH:MM)"""
        if value is None:
            return 'N/A'
        
        try:
            if isinstance(value, str):
                # Intentar extraer hora de diferentes formatos
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%H:%M:%S',
                    '%H:%M',
                    '%d/%m/%Y %H:%M',
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime('%H:%M')
                    except ValueError:
                        continue
                
                # Intentar extraer hora manualmente si tiene formato conocido
                if ':' in value:
                    parts = value.split()
                    for part in parts:
                        if ':' in part and len(part) >= 5:
                            hora_part = part.split(':')[:2]
                            return f"{hora_part[0]}:{hora_part[1]}"
            
            elif isinstance(value, datetime):
                return value.strftime('%H:%M')
            
            return str(value)
            
        except Exception:
            return str(value) if value else 'N/A'

    # Configurar headers de seguridad
    from app.helpers.security_headers import setup_security_headers
    setup_security_headers(app)  # CORRECCIÓN: Aplicar headers de seguridad

    # Registrar blueprint de debug (solo en desarrollo o con DEBUG_ERRORS=1)
    try:
        from app.routes.debug_routes import debug_bp
        app.register_blueprint(debug_bp)
        app.logger.info("✅ Blueprint de debug registrado")
    except ImportError as e:
        app.logger.warning(f"⚠️  No se pudo registrar el blueprint de debug: {e}")
    except Exception as e:
        app.logger.error(f"❌ Error al registrar blueprint de debug: {e}")

    # Middleware para cerrar el sitio al público
    # Controlado por variable de entorno SITE_CLOSED (true/false)
    site_closed = os.environ.get('SITE_CLOSED', 'false').lower() in ('true', '1', 'yes')
    app.config['SITE_CLOSED'] = site_closed
    
    if site_closed:
        app.logger.warning("🔒 SITIO CERRADO AL PÚBLICO - Solo acceso autenticado permitido")
        
        @app.before_request
        def check_site_closed():
            """Bloquea el acceso público si el sitio está cerrado"""
            from flask import request, session, redirect, url_for, render_template_string
            
            # Permitir rutas estáticas
            if request.endpoint and request.endpoint.startswith('static'):
                return None
            
            # Rutas permitidas sin autenticación (login, autenticación)
            allowed_paths = [
                '/login_admin',
                '/scanner/bartender',
                '/scanner/seleccionar_bartender',
                '/caja/login',
                '/guardarropia/login',
            ]
            
            # Verificar si la ruta actual está permitida
            path_allowed = any(request.path.startswith(path) for path in allowed_paths)
            
            # Verificar si el usuario está autenticado (admin, bartender, caja, guardarropía)
            is_authenticated = (
                session.get('admin_logged_in') or
                session.get('bartender') or
                session.get('pos_logged_in') or
                session.get('guardarropia_logged_in')
            )
            
            # Si no está autenticado y la ruta no está permitida, bloquear acceso
            if not is_authenticated and not path_allowed:
                # Si es una petición API, retornar JSON
                if request.path.startswith('/api') or request.is_json:
                    from flask import jsonify
                    return jsonify({'error': 'Sitio cerrado al público. Acceso restringido.'}), 403
                
                # Para otras rutas, redirigir al login de admin
                return redirect(url_for('auth.login_admin'))
            
            return None

    # =========================================================================
    # Gate de acceso al menú principal (visible desde cualquier IP)
    # =========================================================================
    # Si defines MENU_GATE_PIN, la home (/) pedirá PIN antes de mostrar el menú.
    app.config['MENU_GATE_PIN'] = os.environ.get('MENU_GATE_PIN')
    app.config['MENU_GATE_ENABLED'] = bool(app.config['MENU_GATE_PIN'])

    if app.config['MENU_GATE_ENABLED']:
        app.logger.warning("🔐 MENU_GATE activo: se requiere PIN antes del menú principal")
        @app.before_request
        def _menu_gate_before_request():
            from flask import request, session, redirect, url_for

            # Si ya está desbloqueado o es admin, permitir
            if session.get('menu_unlocked') or session.get('admin_logged_in'):
                return None

            # Permitir estáticos
            if request.endpoint and request.endpoint.startswith('static'):
                return None

            # Permitir ver la pantalla de gate (home) y la página pública /bimba
            if request.path in ('/', '/bimba'):
                return None

            # Permitir logins públicos existentes
            allowed_prefixes = (
                '/login_admin',
                '/caja/login',
                '/guardarropia/login',
                '/scanner/',
            )
            if any(request.path.startswith(p) for p in allowed_prefixes):
                return None

            # Todo lo demás requiere pasar por /
            return redirect(url_for('home.index'))

    # =========================================================================
    # Overrides finales: MODO SOLO LOCAL (sin conexiones externas)
    # =========================================================================
    if app.config.get('LOCAL_ONLY', True):
        app.logger.warning("🔒 LOCAL_ONLY activo: deshabilitando integraciones externas")
        app.config.update({
            # POS / API externa
            'API_KEY': None,
            'BASE_API_URL': None,

            # IA / LLMs
            'OPENAI_API_KEY': None,
            'OPENAI_ORGANIZATION_ID': None,
            'OPENAI_PROJECT_ID': None,
            'USE_DIALOGFLOW': False,
            'DIALOGFLOW_PROJECT_ID': None,
            'DIALOGFLOW_CREDENTIALS_PATH': None,

            # n8n
            'N8N_WEBHOOK_URL': None,
            'N8N_WEBHOOK_SECRET': None,
            'N8N_API_KEY': None,

            # Meta / Instagram
            'INSTAGRAM_VERIFY_TOKEN': None,
            'INSTAGRAM_PAGE_ACCESS_TOKEN': None,
            'INSTAGRAM_BUSINESS_ACCOUNT_ID': None,
            'META_APP_ID': None,
            'META_APP_SECRET': None,

            # Email / SMTP
            'SMTP_SERVER': None,
            'SMTP_USER': None,
            'SMTP_PASSWORD': None,
            'SMTP_FROM': None,

            # Pagos (forzar demo / deshabilitar)
            'GETNET_DEMO_MODE': True,
            'SUMUP_API_KEY': None,

            # WhatsApp
            'WHATSAPP_API_KEY': None,
            'WHATSAPP_API_SECRET': None,
            'WHATSAPP_TOKEN': None,
            'TWILIO_ACCOUNT_SID': None,
            'TWILIO_AUTH_TOKEN': None,
        })

    return app# Version bump Sun Dec  7 02:37:54 -03 2025
