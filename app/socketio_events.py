from flask import session, request, current_app
from flask_socketio import emit
from threading import Thread
import time


def register_socketio_events(socketio):

    @socketio.on('connect', namespace='/admin_logs')
    def admin_logs_connect(auth):
        # Verificar si el usuario está autenticado
        # Usar app_context para asegurar acceso correcto a la sesión
        try:
            with current_app.app_context():
                admin_logged_in = session.get('admin_logged_in', False)
                
                if admin_logged_in:
                    current_app.logger.info('✅ Admin WebSocket conectado')
                    emit('status', {'msg': 'Conectado al stream de logs.'})
                else:
                    current_app.logger.warning('❌ Intento NO autorizado de conexión WS')
                    # Permitir conexión pero informar que no está autorizado
                    emit('status', {'msg': 'No autorizado. Por favor, inicia sesión.'})
        except Exception as e:
            current_app.logger.error(f'Error en admin_logs_connect: {e}')
            # Permitir conexión incluso si hay error
            emit('status', {'msg': 'Conectado (modo limitado)'})

    @socketio.on('disconnect', namespace='/admin_logs')
    def admin_logs_disconnect():
        with current_app.app_context():
            current_app.logger.info('Admin WebSocket desconectado')

    @socketio.on('connect', namespace='/admin_stats')
    def admin_stats_connect():
        with current_app.app_context():
            if session.get('admin_logged_in'):
                current_app.logger.info('Admin Stats WebSocket conectado')
                emit('status', {'msg': 'Conectado al stream de estadísticas.'})
            else:
                current_app.logger.warning('Intento NO autorizado de conexión WS stats → desconectando.')
                return False

    @socketio.on('disconnect', namespace='/admin_stats')
    def admin_stats_disconnect():
        with current_app.app_context():
            current_app.logger.info('Admin Stats WebSocket desconectado')
    
    # FASE 8: Visor de Cajas en Tiempo Real
    @socketio.on('connect', namespace='/admin')
    def admin_connect(auth):
        """Conexión al namespace /admin para visor de cajas en tiempo real"""
        with current_app.app_context():
            if session.get('admin_logged_in'):
                current_app.logger.info('✅ Admin conectado al visor de cajas en tiempo real')
                emit('status', {'msg': 'Conectado al visor de cajas en tiempo real'})
            else:
                current_app.logger.warning('❌ Intento NO autorizado de conexión WS /admin')
                return False
    
    @socketio.on('disconnect', namespace='/admin')
    def admin_disconnect():
        with current_app.app_context():
            current_app.logger.info('Admin desconectado del visor de cajas')
    
    @socketio.on('request_metrics', namespace='/admin_stats')
    def handle_request_metrics():
        """Enviar métricas cuando el cliente las solicite"""
        with current_app.app_context():
            if session.get('admin_logged_in'):
                try:
                    from app.helpers.dashboard_metrics_service import get_metrics_service
                    metrics_service = get_metrics_service()
                    metrics = metrics_service.get_all_metrics(use_cache=False)
                    emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
                except Exception as e:
                    current_app.logger.error(f"Error enviando métricas: {e}")
                    emit('error', {'message': 'Error al obtener métricas'}, namespace='/admin_stats')
    
    # Función para emitir métricas periódicamente (se inicializa después de crear la app)
    def start_metrics_thread(app_instance):
        """Iniciar thread para emitir métricas periódicamente"""
        def emit_periodic_metrics():
            """Emitir métricas cada 10 segundos a todos los clientes conectados para tiempo real"""
            while True:
                try:
                    time.sleep(10)  # Esperar 10 segundos para actualización en tiempo real
                    
                    with app_instance.app_context():
                        try:
                            from app.helpers.dashboard_metrics_service import get_metrics_service
                            metrics_service = get_metrics_service()
                            metrics = metrics_service.get_all_metrics(use_cache=True)
                            
                            # Emitir a todos los clientes en /admin_stats
                            socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
                        except Exception as e:
                            app_instance.logger.error(f"Error en emisión periódica de métricas: {e}")
                except Exception as e:
                    app_instance.logger.error(f"Error en thread de métricas periódicas: {e}")
                    time.sleep(60)  # Esperar más tiempo si hay error
        
        try:
            metrics_thread = Thread(target=emit_periodic_metrics, daemon=True)
            metrics_thread.start()
            app_instance.logger.info("✅ Thread de métricas periódicas iniciado")
        except Exception as e:
            app_instance.logger.error(f"Error iniciando thread de métricas: {e}")
    
    # Guardar función para inicializar después
    socketio._start_metrics_thread = start_metrics_thread

    @socketio.on('connect', namespace='/encuesta')
    def survey_connect():
        with current_app.app_context():
            current_app.logger.info('Survey WebSocket conectado')
            emit('status', {'msg': 'Conectado al stream de encuestas.'})

    @socketio.on('disconnect', namespace='/encuesta')
    def survey_disconnect():
        with current_app.app_context():
            current_app.logger.info('Survey WebSocket desconectado')
    
    # FASE 8: Namespace para visor de cajas en tiempo real
    @socketio.on('connect', namespace='/admin')
    def admin_connect():
        with current_app.app_context():
            if session.get('admin_logged_in'):
                current_app.logger.info('✅ Admin visor de cajas conectado')
                emit('status', {'msg': 'Conectado al visor de cajas en tiempo real.'})
            else:
                current_app.logger.warning('❌ Intento NO autorizado de conexión al visor de cajas')
                return False
    
    @socketio.on('disconnect', namespace='/admin')
    def admin_disconnect():
        with current_app.app_context():
            current_app.logger.info('Admin visor de cajas desconectado')