from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for, flash
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import csv
import os

# Imports de servicios (nueva arquitectura)
from app.application.services.service_factory import get_survey_service, get_shift_service
from app.application.dto.survey_dto import SurveyResponseRequest
from app.application.middleware.shift_guard import require_shift_open

survey_bp = Blueprint('survey', __name__, url_prefix='/encuesta')


def ensure_survey_file():
    """Asegura que existe el archivo CSV de encuestas"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de encuestas desde archivo")
    instance_path = get_safe_instance_path() or current_app.instance_path
    survey_file = os.path.join(instance_path, 'survey_responses.csv')
    expected_header = ['timestamp', 'barra', 'rating', 'comment', 'fiesta_nombre', 'djs', 'bartender_nombre', 'fecha_sesion']
    
    if not os.path.exists(survey_file):
        os.makedirs(instance_path, exist_ok=True)
        with open(survey_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(expected_header)
    else:
        # Verificar y actualizar header si es necesario
        try:
            with open(survey_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header != expected_header:
                    # Leer todas las filas existentes
                    rows = list(reader)
                    # Reescribir con nuevo header
                    with open(survey_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(expected_header)
                        # Migrar datos antiguos (agregar columnas vacías si faltan)
                        for row in rows:
                            while len(row) < len(expected_header):
                                row.append('')
                            writer.writerow(row[:len(expected_header)])
        except Exception as e:
            current_app.logger.error(f"Error actualizando header de survey: {e}")
            # Si hay error, crear nuevo archivo
            os.rename(survey_file, survey_file + '.backup')
            with open(survey_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(expected_header)
    
    return survey_file


def ensure_sessions_file():
    """Asegura que existe el archivo CSV de sesiones diarias"""
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de sesiones de encuestas desde archivo")
    instance_path = get_safe_instance_path() or current_app.instance_path
    sessions_file = os.path.join(instance_path, 'survey_sessions.csv')
    
    if not os.path.exists(sessions_file):
        os.makedirs(instance_path, exist_ok=True)
        with open(sessions_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['fecha_sesion', 'fiesta_nombre', 'djs', 'bartenders', 'hora_inicio', 'hora_fin', 'total_respuestas', 'promedio_rating', 'estado'])
    
    return sessions_file


def get_current_session_date():
    """Obtiene la fecha de sesión actual (si es después de 04:30, la sesión es del día anterior)"""
    from app.helpers.timezone_utils import CHILE_TZ
    now = datetime.now(CHILE_TZ)
    # Si es antes de las 04:30, la sesión es del día anterior
    if now.hour < 4 or (now.hour == 4 and now.minute < 30):
        session_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        session_date = now.strftime('%Y-%m-%d')
    return session_date


def get_active_session_info():
    """Obtiene información de la sesión activa actual desde el turno unificado"""
    # Intentar obtener información del turno activo
    try:
        from .helpers.shift_manager_compat import get_shift_status
        shift_status = get_shift_status()
        
        if shift_status.get('is_open', False):
            # Usar información del turno unificado
            # Extraer hora de inicio en formato HH:MM:SS
            hora_inicio = ''
            opened_at = shift_status.get('opened_at', '')
            if opened_at:
                try:
                    # Parsear desde ISO format
                    if 'T' in opened_at:
                        try:
                            parsed = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                            hora_inicio = parsed.strftime('%H:%M:%S')
                        except:
                            # Fallback: extraer solo la parte de hora si es ISO
                            hora_inicio = opened_at.split('T')[1][:8]  # Tomar HH:MM:SS
                    else:
                        # Si ya está en formato legible, extraer solo la hora
                        if len(opened_at) >= 19:
                            hora_inicio = opened_at[11:19]  # Extraer HH:MM:SS
                        elif len(opened_at) >= 16:
                            hora_inicio = opened_at[11:16] + ':00'  # HH:MM -> HH:MM:SS
                except:
                    pass
            
            return {
                'fecha_sesion': shift_status.get('shift_date', ''),
                'fiesta_nombre': shift_status.get('fiesta_nombre', ''),
                'djs': shift_status.get('djs', ''),
                'bartenders': ', '.join(shift_status.get('bartenders', [])) if shift_status.get('bartenders') else '',
                'estado': 'abierta',
                'hora_inicio': hora_inicio or datetime.now().strftime('%H:%M:%S')
            }
    except:
        pass
    
    # Fallback: buscar en sesiones antiguas (compatibilidad)
    sessions_file = ensure_sessions_file()
    session_date = get_current_session_date()
    
    if not os.path.exists(sessions_file):
        return None
    
    try:
        with open(sessions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('fecha_sesion') == session_date and row.get('estado') == 'abierta':
                    return row
    except:
        pass
    
    return None


def is_survey_active():
    """Verifica si la encuesta está activa (siempre activa en modo prueba)"""
    # Modo prueba: siempre activa
    return True
    # Para producción, descomentar:
    # now = datetime.now()
    # current_hour = now.hour
    # current_minute = now.minute
    # if current_hour >= 19 or (current_hour < 4) or (current_hour == 4 and current_minute < 30):
    #     return True
    # return False


def save_survey_response(barra, rating, comment='', fiesta_nombre='', djs='', bartender_nombre=''):
    """Guarda una respuesta de encuesta"""
    survey_file = ensure_survey_file()
    session_date = get_current_session_date()
    
    # Si no se proporciona fiesta_nombre/djs, obtener de la sesión activa
    if not fiesta_nombre or not djs:
        session_info = get_active_session_info()
        if session_info:
            fiesta_nombre = fiesta_nombre or session_info.get('fiesta_nombre', '')
            djs = djs or session_info.get('djs', '')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open(survey_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, barra, rating, comment, fiesta_nombre, djs, bartender_nombre, session_date])
        return True
    except Exception as e:
        current_app.logger.error(f"Error guardando respuesta de encuesta: {e}")
        return False


def load_survey_responses(barra=None, days=None, session_date=None):
    """Carga las respuestas de encuestas"""
    survey_file = ensure_survey_file()
    
    if not os.path.exists(survey_file):
        return []
    
    responses = []
    cutoff_date = None
    if days:
        cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        with open(survey_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Si hay filtro de barra, aplicar
                if barra and row.get('barra') != barra:
                    continue
                
                # Si hay filtro de sesión, aplicar
                if session_date and row.get('fecha_sesion') != session_date:
                    continue
                
                # Si hay filtro de días, aplicar
                if cutoff_date:
                    try:
                        response_date = datetime.strptime(row.get('timestamp', ''), '%Y-%m-%d %H:%M:%S')
                        if response_date < cutoff_date:
                            continue
                    except:
                        pass
                
                responses.append(row)
    except Exception as e:
        current_app.logger.error(f"Error cargando respuestas: {e}")
    
    return responses


@survey_bp.route('/barra/<int:barra_num>')
def survey_tablet(barra_num):
    """Vista para tablet en barra específica"""
    if barra_num not in [1, 2]:
        return "Barra no válida", 404
    
    # Verificar si está activa
    if not is_survey_active():
        return render_template('survey/inactive.html', 
                             message="Las encuestas están cerradas. Horario: 19:00 - 04:30")
    
    # Obtener información de la sesión activa
    session_info = get_active_session_info()
    
    # Obtener bartenders desde la API
    from .helpers.pos_api import get_employees
    bartenders = get_employees(only_bartenders=True)
    
    # Si no hay sesión activa, mostrar mensaje al cliente (no formulario)
    # El formulario de inicio de sesión está solo en /survey/session_manager
    
    return render_template('survey/tablet.html', 
                         barra=barra_num, 
                         session_info=session_info,
                         bartenders=bartenders)


@survey_bp.route('/submit', methods=['POST'])
@require_shift_open
def submit_survey():
    """Endpoint para enviar una respuesta de encuesta - Thin controller usando SurveyService"""
    # Usar servicio de encuestas
    survey_service = get_survey_service()
    
    # Verificar si está activa (además de turno abierto)
    # Nota: El decorador @require_shift_open ya valida que haya turno abierto
    # Las encuestas están siempre activas en modo prueba, se puede agregar validación de horario si es necesario
    
    data = request.json
    
    barra = data.get('barra')
    rating = data.get('rating')
    comment = data.get('comment', '')
    fiesta_nombre = data.get('fiesta_nombre', '')
    djs = data.get('djs', '')
    bartender_nombre = data.get('bartender_nombre', '')
    
    if not barra or rating is None:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    # Normalizar barra
    barra = str(barra)
    
    # Mapear ratings: excelente=5, bueno=3, medio=2, deficiente=1
    # Aceptar tanto números como strings para retrocompatibilidad
    if isinstance(rating, str):
        rating_map = {'excelente': 5, 'bueno': 3, 'medio': 2, 'deficiente': 1}
        rating = rating_map.get(rating.lower(), rating)
    
    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return jsonify({'error': 'Rating inválido'}), 400
    
    # Crear DTO
    survey_request = SurveyResponseRequest(
        barra=barra,
        rating=rating,
        comment=comment if comment else None,
        fiesta_nombre=fiesta_nombre if fiesta_nombre else None,
        djs=djs if djs else None,
        bartender_nombre=bartender_nombre if bartender_nombre else None
    )
    
    # Validar y guardar usando servicio
    try:
        success, message = survey_service.save_survey_response(survey_request)
        if success:
            # Emitir evento SocketIO para actualizar dashboard en tiempo real
            # El servicio ya emite el evento internamente, pero podemos mantener compatibilidad
            from app import socketio
            socketio.emit('new_survey_response', {
                'barra': barra,
                'rating': rating,
                'comment': comment,
                'fiesta_nombre': fiesta_nombre,
                'djs': djs,
                'bartender_nombre': bartender_nombre,
                'timestamp': datetime.now().isoformat()
            }, namespace='/encuesta')
            return jsonify({'success': True, 'message': message or '¡Gracias por tu opinión!'})
        else:
            return jsonify({'error': message or 'Error al guardar respuesta'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error guardando respuesta de encuesta: {e}")
        return jsonify({'error': 'Error interno al guardar respuesta'}), 500


@survey_bp.route('/admin')
def survey_admin():
    """Dashboard de administración de encuestas"""
    # Verificar autenticación de admin
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "info")
        return redirect(url_for('routes.login_admin'))
    
    return render_template('survey/admin.html')


@survey_bp.route('/api/results')
def api_results():
    """API para obtener resultados de encuestas de la sesión activa - Thin controller usando SurveyService"""
    barra = request.args.get('barra')  # Opcional: filtrar por barra
    
    # Usar servicio de encuestas
    survey_service = get_survey_service()
    
    # Verificar si hay turno abierto - si no hay, retornar datos vacíos
    shift_service = get_shift_service()
    if not shift_service.is_shift_open():
        # Si no hay turno abierto, retornar datos vacíos
        return jsonify({
            'total': 0,
            'average_rating': 0,
            'ratings_count': {},
            'by_barra': {},
            'by_hour': {},
            'recent_responses': [],
            'session_info': None,
            'session_date': None
        })
    
    # Obtener resultados usando el servicio
    stats = survey_service.get_survey_results(barra=barra)
    
    return jsonify(stats)


@survey_bp.route('/api/realtime')
def api_realtime():
    """Endpoint para conexión SocketIO en tiempo real"""
    return jsonify({'status': 'ok', 'namespace': '/encuesta'})


@survey_bp.route('/api/status')
def api_status():
    """API para verificar estado de la encuesta"""
    active = is_survey_active()
    session_info = get_active_session_info()
    
    return jsonify({
        'active': active,
        'session_info': session_info,
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@survey_bp.route('/api/start_session', methods=['POST'])
def start_session():
    """Inicia una nueva sesión de fiesta"""
    # Validación de horario desactivada en modo prueba
    # if not is_survey_active():
    #     return jsonify({'error': 'Las encuestas solo están activas de 19:00 a 04:30'}), 403
    
    data = request.json
    fiesta_nombre = data.get('fiesta_nombre', '').strip()
    djs = data.get('djs', '').strip()
    bartenders = data.get('bartenders', [])  # Lista de nombres de bartenders
    
    if not fiesta_nombre:
        return jsonify({'error': 'El nombre de la fiesta es requerido'}), 400
    
    # Verificar si ya existe una sesión abierta para hoy
    session_info = get_active_session_info()
    if session_info:
        return jsonify({'error': 'Ya existe una sesión abierta para hoy', 'session': session_info}), 400
    
    sessions_file = ensure_sessions_file()
    session_date = get_current_session_date()
    hora_inicio = datetime.now().strftime('%H:%M:%S')
    bartenders_str = ', '.join(bartenders) if bartenders else ''
    
    # Crear nueva sesión
    with open(sessions_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([session_date, fiesta_nombre, djs, bartenders_str, hora_inicio, '', 0, 0.0, 'abierta'])
    
    return jsonify({
        'success': True,
        'message': 'Sesión iniciada correctamente',
        'session_date': session_date,
        'fiesta_nombre': fiesta_nombre
    })


@survey_bp.route('/api/close_session', methods=['POST'])
def close_session():
    """Cierra la sesión actual y genera estadísticas - Thin controller usando SurveyService"""
    # Usar servicio de encuestas
    survey_service = get_survey_service()
    
    session_date = request.json.get('session_date') if request.is_json else None
    if not session_date:
        session_date = survey_service._get_current_session_date()
    
    # Cerrar sesión usando servicio
    try:
        success, message = survey_service.close_session(session_date)
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Error cerrando sesión: {e}")
        return jsonify({'error': 'Error interno al cerrar sesión'}), 500


@survey_bp.route('/history')
def survey_history():
    """Vista de historial de fiestas"""
    return render_template('survey/history.html')


@survey_bp.route('/history/<session_date>')
def survey_session_detail(session_date):
    """Vista detallada de una sesión específica - Thin controller usando SurveyService"""
    # Usar servicio de encuestas
    survey_service = get_survey_service()
    
    # Obtener resumen de la sesión usando servicio
    summary = survey_service.get_session_summary(session_date)
    
    if not summary:
        flash(f"No se encontró sesión para la fecha {session_date}", "error")
        return redirect(url_for('survey.survey_history'))
    
    # Convertir resumen a formato compatible con el template
    # El template espera 'stats' y 'session_info' como objetos separados
    stats = {
        'session_date': summary.get('fecha_sesion', session_date),
        'total_respuestas': summary.get('total_respuestas', 0),
        'average_rating': summary.get('promedio_rating', 0.0),
        'ratings_count': summary.get('ratings_count', {}),
        'by_barra': summary.get('barra_stats', {}),
        'by_bartender': {},
        'by_hour': {},
        'responses': []
    }
    
    session_info = {
        'fecha_sesion': summary.get('fecha_sesion', session_date),
        'fiesta_nombre': summary.get('fiesta_nombre', ''),
        'djs': summary.get('djs', ''),
        'bartenders': summary.get('bartenders', ''),
        'hora_inicio': summary.get('hora_inicio', ''),
        'hora_fin': summary.get('hora_fin', ''),
        'estado': summary.get('estado', 'cerrada')
    }
    
    return render_template('survey/session_detail.html', session_date=session_date, stats=stats, session_info=session_info)


@survey_bp.route('/session_manager')
def session_manager():
    """Vista de gestión de sesiones"""
    from .helpers.pos_api import get_employees
    bartenders = get_employees(only_bartenders=True)
    return render_template('survey/session_manager.html', bartenders=bartenders)


@survey_bp.route('/api/bartenders')
def api_bartenders():
    """API para obtener lista de bartenders - Thin controller usando servicio"""
    # Usar servicio de delivery para acceder al POS client
    from app.application.services.service_factory import get_delivery_service
    delivery_service = get_delivery_service()
    bartenders = delivery_service.pos_client.get_employees(only_bartenders=True)
    
    bartenders_list = []
    for bartender in bartenders:
        name = bartender.get('name') or f"{bartender.get('first_name', '')} {bartender.get('last_name', '')}".strip()
        bartenders_list.append({
            'id': bartender.get('person_id') or bartender.get('employee_id') or bartender.get('id'),
            'name': name,
            'first_name': bartender.get('first_name', ''),
            'last_name': bartender.get('last_name', '')
        })
    
    return jsonify(bartenders_list)


@survey_bp.route('/api/history')
def api_history():
    """API para obtener historial de sesiones"""
    sessions_file = ensure_sessions_file()
    
    if not os.path.exists(sessions_file):
        return jsonify({'sessions': []})
    
    sessions = []
    try:
        with open(sessions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            sessions = list(reader)
        
        # Ordenar por fecha descendente
        sessions.sort(key=lambda x: x.get('fecha_sesion', ''), reverse=True)
    except Exception as e:
        current_app.logger.error(f"Error cargando historial: {e}")
    
    return jsonify({'sessions': sessions})


@survey_bp.route('/api/session_stats/<session_date>')
def session_stats(session_date):
    """Obtiene estadísticas detalladas de una sesión - Thin controller usando SurveyService"""
    # Usar servicio de encuestas
    survey_service = get_survey_service()
    
    # Obtener resumen de la sesión usando servicio
    summary = survey_service.get_session_summary(session_date)
    
    if not summary:
        return jsonify({'error': f'No se encontró sesión para la fecha {session_date}'}), 404
    
    return jsonify(summary)


@survey_bp.route('/api/all-responses')
def api_all_responses():
    """API para obtener todas las respuestas de encuestas con filtros opcionales"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        survey_service = get_survey_service()
        
        # Obtener todas las respuestas
        all_responses = survey_service.get_all_responses()
        
        # Convertir a formato JSON
        responses_data = []
        for response in all_responses:
            responses_data.append({
                'id': response.id if hasattr(response, 'id') else None,
                'timestamp': response.timestamp if isinstance(response.timestamp, str) else response.timestamp.isoformat() if hasattr(response.timestamp, 'isoformat') else str(response.timestamp),
                'barra': response.barra,
                'rating': response.rating,
                'comment': response.comment or '',
                'fiesta_nombre': response.fiesta_nombre or '',
                'djs': response.djs or '',
                'bartender_nombre': response.bartender_nombre or '',
                'fecha_sesion': response.fecha_sesion if isinstance(response.fecha_sesion, str) else response.fecha_sesion.isoformat() if hasattr(response.fecha_sesion, 'isoformat') else str(response.fecha_sesion)
            })
        
        # Ordenar por fecha más reciente primero
        responses_data.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'responses': responses_data,
            'total': len(responses_data)
        })
    except Exception as e:
        current_app.logger.error(f"Error obteniendo todas las respuestas: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Error interno al obtener respuestas'}), 500


@survey_bp.route('/api/export/csv')
def api_export_csv():
    """API para exportar respuestas en formato CSV"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        survey_service = get_survey_service()
        
        # Obtener filtros
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        barra = request.args.get('barra')
        
        # Obtener todas las respuestas
        all_responses = survey_service.get_all_responses()
        
        # Aplicar filtros
        filtered_responses = []
        for response in all_responses:
            # Filtro por fecha
            if date_from:
                response_date = response.fecha_sesion if isinstance(response.fecha_sesion, str) else response.fecha_sesion.isoformat() if hasattr(response.fecha_sesion, 'isoformat') else str(response.fecha_sesion)
                if response_date < date_from:
                    continue
            
            if date_to:
                response_date = response.fecha_sesion if isinstance(response.fecha_sesion, str) else response.fecha_sesion.isoformat() if hasattr(response.fecha_sesion, 'isoformat') else str(response.fecha_sesion)
                if response_date > date_to:
                    continue
            
            # Filtro por barra
            if barra and response.barra != barra:
                continue
            
            filtered_responses.append(response)
        
        # Crear CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Fecha/Hora', 'Barra', 'Calificación', 'Comentario',
            'Fiesta', 'DJs', 'Bartender', 'Fecha Sesión'
        ])
        
        # Datos
        for response in filtered_responses:
            timestamp = response.timestamp if isinstance(response.timestamp, str) else response.timestamp.isoformat() if hasattr(response.timestamp, 'isoformat') else str(response.timestamp)
            fecha_sesion = response.fecha_sesion if isinstance(response.fecha_sesion, str) else response.fecha_sesion.isoformat() if hasattr(response.fecha_sesion, 'isoformat') else str(response.fecha_sesion)
            
            writer.writerow([
                timestamp,
                response.barra,
                response.rating,
                response.comment or '',
                response.fiesta_nombre or '',
                response.djs or '',
                response.bartender_nombre or '',
                fecha_sesion
            ])
        
        # Preparar respuesta
        output.seek(0)
        filename = f'encuestas_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error exportando CSV: {e}", exc_info=True)
        return jsonify({'error': 'Error al exportar CSV'}), 500


@survey_bp.route('/api/export/stats')
def api_export_stats():
    """API para exportar estadísticas de sesiones"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from flask import Response
        import csv
        from io import StringIO
        
        survey_service = get_survey_service()
        
        # Obtener todas las sesiones
        sessions_file = ensure_sessions_file()
        sessions = []
        
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                sessions = list(reader)
        
        # Crear CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Fecha Sesión', 'Fiesta', 'DJs', 'Bartenders',
            'Hora Inicio', 'Hora Fin', 'Total Respuestas', 'Promedio Rating', 'Estado'
        ])
        
        # Datos
        for session in sessions:
            writer.writerow([
                session.get('fecha_sesion', ''),
                session.get('fiesta_nombre', ''),
                session.get('djs', ''),
                session.get('bartenders', ''),
                session.get('hora_inicio', ''),
                session.get('hora_fin', ''),
                session.get('total_respuestas', '0'),
                session.get('promedio_rating', '0.0'),
                session.get('estado', '')
            ])
        
        # Preparar respuesta
        output.seek(0)
        filename = f'estadisticas_encuestas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error exportando estadísticas: {e}", exc_info=True)
        return jsonify({'error': 'Error al exportar estadísticas'}), 500

