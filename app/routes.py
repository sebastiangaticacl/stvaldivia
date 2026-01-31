"""
Rutas principales del sistema BIMBA
"""
import os
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash, current_app
from datetime import datetime, date
from app.application.services.jornada_service import JornadaService
from app.application.dto.jornada_dto import (
    CrearJornadaRequest, AsignarResponsablesRequest, AbrirLocalRequest
)
from app.models.jornada_models import Jornada, PlanillaTrabajador
from app.models import db

# Crear blueprint principal (puede estar vacío si las rutas están en otros módulos)
bp = Blueprint('routes', __name__)

# Las rutas principales están definidas en otros módulos/blueprints
# Este blueprint puede usarse para rutas comunes si es necesario

@bp.route('/admin')
def admin():
    """Redirigir /admin a /admin/dashboard"""
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return redirect(url_for('routes.admin_dashboard'))

@bp.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard administrativo"""
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Obtener todas las métricas usando el servicio
    try:
        from app.helpers.dashboard_metrics_service import get_metrics_service
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_all_metrics(use_cache=True)
    except Exception as e:
        current_app.logger.error(f"Error al cargar métricas del dashboard: {e}", exc_info=True)
        metrics = None
    
    return render_template('admin_dashboard.html', metrics=metrics)


@bp.route('/admin/logs')
def admin_logs():
    """Logs de entregas - redirige a admin_area"""
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Obtener parámetros de paginación
    page = request.args.get('page', 1, type=int)
    turno = request.args.get('turno', 'false')
    per_page = request.args.get('per_page', 50, type=int)
    
    # Variables básicas para el template
    filter_by_turno = turno == 'true'
    current_page = page
    total_logs = 0  # Los logs se cargan dinámicamente via JavaScript/SocketIO
    logs = []  # Lista vacía - los logs se cargan dinámicamente
    
    # Calcular paginación (valores por defecto para evitar errores en el template)
    total_pages = 1
    has_prev = False
    has_next = False
    
    # Renderizar admin_area.html que parece ser la página principal de logs
    return render_template('admin_area.html',
                         filter_by_turno=filter_by_turno,
                         current_page=current_page,
                         per_page=per_page,
                         total_logs=total_logs,
                         logs=logs,
                         total_pages=total_pages,
                         has_prev=has_prev,
                         has_next=has_next)


@bp.route('/admin/pos_stats')
def pos_stats():
    """Redirigir a dashboard - módulo de cajas eliminado"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    flash('El módulo de gestión de cajas ha sido eliminado.', 'info')
    return redirect(url_for('routes.admin_dashboard'))


@bp.route('/admin/api/register/toggle', methods=['POST'])
def api_toggle_register():
    """API deshabilitada - módulo de cajas eliminado"""
    return jsonify({'success': False, 'error': 'Módulo de gestión de cajas eliminado'}), 410

@bp.route('/admin/api/register/clear-all', methods=['POST'])
def api_clear_all_registers():
    """API: Desbloquear todas las cajas"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.register_lock_db import unlock_all_registers
        
        count = unlock_all_registers()
        
        if count > 0:
            # Emitir actualización de métricas
            try:
                from app import socketio
                from app.helpers.dashboard_metrics_service import get_metrics_service
                
                metrics_service = get_metrics_service()
                metrics = metrics_service.get_all_metrics(use_cache=False)
                socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
            except Exception as e:
                current_app.logger.warning(f"No se pudo emitir actualización: {e}")
        
        return jsonify({
            'success': True,
            'message': f'{count} caja(s) desbloqueada(s)',
            'count': count
        })
    except Exception as e:
        current_app.logger.error(f"Error al desbloquear todas las cajas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/panel_control')
def admin_panel_control():
    """Panel de control administrativo"""
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Verificar si es superadmin
    username = session.get('admin_username', '').lower()
    is_superadmin = (username == 'sebagatica')
    
    # Crear información del sistema
    from app.helpers.timezone_utils import CHILE_TZ
    from datetime import datetime, timedelta
    
    now = datetime.now(CHILE_TZ)
    
    # Nombres de días en español
    days_spanish = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    
    day_name_english = now.strftime('%A')
    day_name = days_spanish.get(day_name_english, day_name_english)
    
    system_info = {
        'current_time': now.strftime('%H:%M:%S'),
        'current_date': now.strftime('%d/%m/%Y'),
        'day_name': day_name,
        'timezone': 'America/Santiago (CLT)'
    }
    
    # Obtener logs de auditoría (solo para superadmin)
    audit_logs = []
    audit_alerts_count = 0
    if is_superadmin:
        try:
            from app.models.audit_log_models import AuditLog
            from app.models.cargo_audit_models import CargoSalaryAuditLog
            
            # Obtener últimos 100 logs de auditoría general
            audit_logs_general = AuditLog.query.order_by(
                AuditLog.timestamp.desc()
            ).limit(100).all()
            
            # Obtener últimos 50 logs de auditoría de cargos/sueldos
            audit_logs_cargos = CargoSalaryAuditLog.query.order_by(
                CargoSalaryAuditLog.created_at.desc()
            ).limit(50).all()
            
            # Combinar y ordenar por fecha
            all_logs = []
            for log in audit_logs_general:
                all_logs.append({
                    'type': 'general',
                    'id': log.id,
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'username': log.username or 'unknown',
                    'timestamp': log.timestamp,
                    'success': log.success,
                    'old_value': log.old_value,
                    'new_value': log.new_value,
                    'ip_address': log.ip_address
                })
            
            for log in audit_logs_cargos:
                all_logs.append({
                    'type': 'cargo_salary',
                    'id': log.id,
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'cargo_nombre': log.cargo_nombre,
                    'username': log.changed_by_username or 'unknown',
                    'timestamp': log.created_at,
                    'success': True,
                    'old_values': log.old_values,
                    'new_values': log.new_values,
                    'ip_address': log.ip_address
                })
            
            # Ordenar por timestamp descendente
            all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            audit_logs = all_logs[:100]  # Limitar a 100 más recientes
            
            # Contar acciones que requieren atención (últimas 24 horas)
            last_24h = now - timedelta(hours=24)
            recent_logs = [log for log in all_logs if log['timestamp'] >= last_24h]
            
            # Contar acciones críticas que requieren revisión
            critical_actions = ['delete', 'update_salary', 'mark_payment', 'close_shift', 'update']
            audit_alerts_count = sum(1 for log in recent_logs 
                                    if log['action'] in critical_actions or 
                                    (log['type'] == 'cargo_salary' and log['action'] in ['update', 'delete']))
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener logs de auditoría: {e}", exc_info=True)
            audit_logs = []
            audit_alerts_count = 0
    
    # Obtener información de base de datos actual
    try:
        from app.helpers.database_config_helper import get_current_database_info
        db_info = get_current_database_info()
    except Exception as e:
        current_app.logger.error(f"Error al obtener info de BD: {e}", exc_info=True)
        db_info = {'mode': 'prod', 'url': 'No disponible'}
    
    return render_template('admin/panel_control.html', 
                         system_info=system_info,
                         is_superadmin=is_superadmin,
                         audit_logs=audit_logs,
                         audit_alerts_count=audit_alerts_count,
                         db_info=db_info)


@bp.route('/admin/panel_control/logs')
def admin_panel_control_logs():
    """Vista de logs del sistema dentro del panel de control"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from flask import request
        from app.models import db
        from app.models.delivery_models import Delivery
        from sqlalchemy import or_
        
        # Parámetros de filtrado
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        bartender_filter = request.args.get('bartender', '').strip()
        barra_filter = request.args.get('barra', '').strip()
        sale_id_filter = request.args.get('sale_id', '').strip()
        
        # Optimizar: filtrar directamente en la base de datos
        
        # Query base
        query = Delivery.query
        
        # Aplicar filtros en la base de datos
        if search:
            from sqlalchemy import func
            search_pattern = f"%{search}%"
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(
                or_(
                    func.lower(Delivery.sale_id).like(func.lower(search_pattern)),
                    func.lower(Delivery.item_name).like(func.lower(search_pattern)),
                    func.lower(Delivery.bartender).like(func.lower(search_pattern)),
                    func.lower(Delivery.barra).like(func.lower(search_pattern))
                )
            )
        
        if bartender_filter:
            from sqlalchemy import func
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(func.lower(Delivery.bartender).like(func.lower(f"%{bartender_filter}%")))
        
        if barra_filter:
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(func.lower(Delivery.barra).like(func.lower(f"%{barra_filter}%")))
        
        if sale_id_filter:
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(func.lower(Delivery.sale_id).like(func.lower(f"%{sale_id_filter}%")))
        
        # Contar total (antes de paginar)
        total_logs = query.count()
        total_pages = (total_logs + per_page - 1) // per_page
        
        # Aplicar ordenamiento y paginación
        deliveries = query.order_by(Delivery.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Convertir a formato de lista para el template
        paginated_logs = [delivery.to_csv_row() for delivery in deliveries]
        
        # Obtener valores únicos para los selectores de filtro (solo una vez, sin filtros)
        all_bartenders = sorted(set(
            result[0] for result in 
            db.session.query(Delivery.bartender).distinct().filter(Delivery.bartender.isnot(None)).all()
            if result[0]
        ))
        all_barras = sorted(set(
            result[0] for result in 
            db.session.query(Delivery.barra).distinct().filter(Delivery.barra.isnot(None)).all()
            if result[0]
        ))
        
        return render_template(
            'admin/panel_control_logs.html',
            logs=paginated_logs,
            page=page,
            per_page=per_page,
            total_logs=total_logs,
            total_pages=total_pages,
            search=search,
            bartender_filter=bartender_filter,
            barra_filter=barra_filter,
            sale_id_filter=sale_id_filter,
            all_bartenders=all_bartenders,
            all_barras=all_barras,
            has_prev=page > 1,
            has_next=page < total_pages
        )
    except Exception as e:
        current_app.logger.error(f"Error al cargar logs: {e}", exc_info=True)
        flash(f'Error al cargar logs: {str(e)}', 'error')
        return redirect(url_for('routes.admin_panel_control'))


@bp.route('/admin/panel_control/db_monitor')
def admin_db_monitor():
    """Monitor de base de datos con estadísticas detalladas"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.helpers.db_monitor import get_database_stats
        db_stats = get_database_stats()
        
        return render_template('admin/db_monitor.html', db_stats=db_stats)
    except Exception as e:
        current_app.logger.error(f"Error al cargar monitor de DB: {e}", exc_info=True)
        flash(f'Error al cargar monitor de DB: {str(e)}', 'error')
        return redirect(url_for('routes.admin_panel_control'))


@bp.route('/admin/api/database/switch', methods=['POST'])
def admin_api_database_switch():
    """API para cambiar entre base de datos de desarrollo y producción"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    # Solo superadmin puede cambiar base de datos
    username = session.get('admin_username', '').lower()
    is_superadmin = (username == 'sebagatica')
    
    if not is_superadmin:
        return jsonify({'error': 'Solo superadmin puede cambiar la base de datos'}), 403
    
    try:
        data = request.get_json()
        mode = data.get('mode')  # 'dev' o 'prod'
        
        if mode not in ['dev', 'prod']:
            return jsonify({'error': 'Modo inválido. Debe ser "dev" o "prod"'}), 400
        
        from app.helpers.database_config_helper import (
            set_database_mode, 
            get_current_database_info,
            get_database_url_for_mode
        )
        import os
        
        # Cambiar modo
        success = set_database_mode(mode, updated_by=username)
        
        if not success:
            return jsonify({'error': 'Error al guardar configuración'}), 500
        
        # Obtener URL para el modo seleccionado
        # Primero intentar desde configuración guardada, luego desde variables de entorno
        if mode == 'dev':
            db_url = get_database_url_for_mode('dev') or os.environ.get('DATABASE_DEV_URL') or os.environ.get('DATABASE_URL')
        else:
            db_url = get_database_url_for_mode('prod') or os.environ.get('DATABASE_PROD_URL') or os.environ.get('DATABASE_URL')
        
        # Obtener información actualizada
        db_info = get_current_database_info()
        db_info['url'] = db_url  # Agregar URL real (se ocultará password en el frontend)
        
        # Registrar en logs de auditoría
        try:
            from app.models.audit_log_models import AuditLog
            audit = AuditLog(
                action='change_database_mode',
                entity_type='system_config',
                username=username,
                success=True,
                new_value=f"database_mode={mode}",
                ip_address=request.remote_addr
            )
            db.session.add(audit)
            db.session.commit()
        except Exception as e:
            current_app.logger.warning(f"Error al registrar auditoría: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Base de datos cambiada a {mode.upper()}',
            'db_info': db_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al cambiar base de datos: {e}", exc_info=True)
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/admin/api/database/info', methods=['GET'])
def admin_api_database_info():
    """API para obtener información de la base de datos actual"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from app.helpers.database_config_helper import get_current_database_info
        db_info = get_current_database_info()
        return jsonify(db_info)
    except Exception as e:
        current_app.logger.error(f"Error al obtener info de BD: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@bp.route('/admin/panel_control/monitoreo')
def admin_monitoreo_servicios():
    """Módulo de monitoreo de servicios del sistema"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.services.monitoring_service import get_monitoring_service
        monitoring_service = get_monitoring_service()
        monitoring_data = monitoring_service.get_all_services_monitoring()
        
        return render_template('admin/monitoreo_servicios.html', 
                             monitoring_data=monitoring_data)
    except Exception as e:
        current_app.logger.error(f"Error al cargar monitoreo de servicios: {e}", exc_info=True)
        flash(f'Error al cargar monitoreo: {str(e)}', 'error')
        return redirect(url_for('routes.admin_panel_control'))


@bp.route('/admin/api/monitoreo/status')
def api_monitoreo_status():
    """API endpoint para obtener estado de servicios (para actualización en tiempo real)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autenticado'}), 401
    
    try:
        from app.services.monitoring_service import get_monitoring_service
        monitoring_service = get_monitoring_service()
        monitoring_data = monitoring_service.get_all_services_monitoring()
        
        return jsonify({
            'success': True,
            'data': monitoring_data
        })
    except Exception as e:
        current_app.logger.error(f"Error en API de monitoreo: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/turnos')
def admin_turnos():
    """Gestión de turnos y jornadas"""
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from datetime import datetime
        # Importar CHILE_TZ desde módulo único de timezone
        try:
            from app.utils.timezone import CHILE_TZ
        except ImportError:
            # Fallback: usar timezone_utils si existe
            try:
                from app.helpers.timezone_utils import CHILE_TZ
            except ImportError:
                current_app.logger.error("No se pudo importar CHILE_TZ desde ningún módulo")
                return jsonify({'error': 'Error de configuración de timezone'}), 500
        
        from app.models.jornada_models import Jornada, PlanillaTrabajador
        
        # Obtener fecha de hoy (fecha_jornada es String en la BD)
        try:
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        except Exception as e:
            current_app.logger.error(f"Error al obtener fecha_hoy: {e}")
            # Fallback a UTC si hay problema con timezone
            fecha_hoy = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Obtener jornada_id de query params si existe
        jornada_id = request.args.get('jornada_id', type=int)
        
        # Obtener jornada actual o la jornada especificada
        # IMPORTANTE: Solo mostrar turnos en estado "preparando" o "abierto" en los workflow steps
        # Los turnos cerrados no deben aparecer como "jornada_actual" para mantener limpio el workflow
        jornada_actual = None
        try:
            if jornada_id:
                jornada_actual = Jornada.query.get(jornada_id)
                # Si el turno está cerrado y no se especificó jornada_id explícitamente, no mostrarlo como actual
                if jornada_actual and jornada_actual.estado_apertura == 'cerrado' and not request.args.get('jornada_id'):
                    jornada_actual = None
            else:
                # Primero buscar turno abierto (sin importar la fecha)
                try:
                    jornada_actual = Jornada.query.filter_by(
                        estado_apertura='abierto',
                        eliminado_en=None  # Excluir eliminados
                    ).order_by(Jornada.fecha_jornada.desc(), Jornada.creado_en.desc()).first()
                except Exception as e:
                    current_app.logger.warning(f"Error al buscar turno abierto: {e}")
                    jornada_actual = None
                
                # Si no hay turno abierto, buscar jornada en estado "preparando" para la fecha de hoy
                # NO mostrar turnos cerrados en los workflow steps
                if not jornada_actual:
                    try:
                        jornada_actual = Jornada.query.filter(
                            Jornada.fecha_jornada == fecha_hoy,
                            Jornada.estado_apertura.in_(['preparando', 'abierto']),  # Solo preparando o abierto
                            Jornada.eliminado_en.is_(None)  # Excluir eliminados
                        ).order_by(Jornada.creado_en.desc()).first()
                    except Exception as e:
                        current_app.logger.warning(f"Error al buscar jornada para fecha {fecha_hoy}: {e}")
                        jornada_actual = None
        except Exception as e:
            current_app.logger.error(f"Error al obtener jornada_actual: {e}", exc_info=True)
            jornada_actual = None
        
        # CONSULTA BD: Obtener planilla de trabajadores ordenada (importante para estadísticas)
        # IMPORTANTE: Solo cargar planilla si el turno NO está cerrado (para mantener workflow limpio)
        planilla_trabajadores = []
        if jornada_actual and jornada_actual.estado_apertura != 'cerrado':
            try:
                planilla_trabajadores = PlanillaTrabajador.query.filter_by(
                    jornada_id=jornada_actual.id
                ).order_by(
                    PlanillaTrabajador.rol.asc(),  # Ordenar por rol primero
                    PlanillaTrabajador.nombre_empleado.asc(),  # Luego por nombre
                    PlanillaTrabajador.creado_en.asc()  # Finalmente por fecha de creación
                ).all()
            except Exception as e:
                current_app.logger.error(f"Error al obtener planilla_trabajadores para jornada {jornada_actual.id}: {e}", exc_info=True)
                planilla_trabajadores = []
        
        # CONSULTA BD: Obtener historial de jornadas con filtros y ordenamiento
        # Parámetros de filtrado
        filtro_estado = request.args.get('filtro_estado', '')  # 'abierto', 'cerrado', 'preparando', o '' para todos
        filtro_tipo = request.args.get('filtro_tipo', '')  # 'Noche', 'Día', 'Especial', o '' para todos
        filtro_fecha_desde = request.args.get('filtro_fecha_desde', '')
        filtro_fecha_hasta = request.args.get('filtro_fecha_hasta', '')
        ordenar_por = request.args.get('ordenar_por', 'fecha_desc')  # 'fecha_desc', 'fecha_asc', 'creado_desc', 'creado_asc'
        mostrar_todos = request.args.get('mostrar_todos', 'false') == 'true'  # Mostrar todos o solo últimos 20
        mostrar_eliminados = request.args.get('mostrar_eliminados', 'false') == 'true'  # Mostrar turnos eliminados
        mostrar_todos_tipos = request.args.get('mostrar_todos_tipos', 'false') == 'true'  # Mostrar activos Y eliminados juntos
        
        # Inicializar variables por defecto
        jornadas_historial = []
        total_jornadas = 0
        
        try:
            # Construir query base - manejar filtro de eliminados
            if mostrar_todos_tipos:
                # Mostrar TODOS los turnos (activos y eliminados)
                query_historial = Jornada.query
            elif mostrar_eliminados:
                # Mostrar solo turnos eliminados
                query_historial = Jornada.query.filter(Jornada.eliminado_en.isnot(None))
            else:
                # Mostrar solo turnos no eliminados (comportamiento por defecto)
                query_historial = Jornada.query.filter(Jornada.eliminado_en.is_(None))
            
            # Aplicar filtros
            if filtro_estado:
                query_historial = query_historial.filter(Jornada.estado_apertura == filtro_estado)
            
            if filtro_tipo:
                query_historial = query_historial.filter(Jornada.tipo_turno == filtro_tipo)
            
            if filtro_fecha_desde:
                try:
                    # fecha_jornada es String, comparar como string
                    fecha_desde_str = filtro_fecha_desde  # Ya está en formato 'YYYY-MM-DD'
                    query_historial = query_historial.filter(Jornada.fecha_jornada >= fecha_desde_str)
                except (ValueError, Exception) as e:
                    current_app.logger.warning(f"Error al aplicar filtro fecha_desde: {e}")
                    pass
            
            if filtro_fecha_hasta:
                try:
                    # fecha_jornada es String, comparar como string
                    fecha_hasta_str = filtro_fecha_hasta  # Ya está en formato 'YYYY-MM-DD'
                    query_historial = query_historial.filter(Jornada.fecha_jornada <= fecha_hasta_str)
                except (ValueError, Exception) as e:
                    current_app.logger.warning(f"Error al aplicar filtro fecha_hasta: {e}")
                    pass
            
            # Aplicar ordenamiento
            if ordenar_por == 'fecha_asc':
                query_historial = query_historial.order_by(
                    Jornada.fecha_jornada.asc(),
                    Jornada.creado_en.asc()
                )
            elif ordenar_por == 'fecha_desc':
                query_historial = query_historial.order_by(
                    Jornada.fecha_jornada.desc(),
                    Jornada.creado_en.desc()
                )
            elif ordenar_por == 'creado_asc':
                query_historial = query_historial.order_by(
                    Jornada.creado_en.asc(),
                    Jornada.fecha_jornada.asc()
                )
            elif ordenar_por == 'creado_desc':
                query_historial = query_historial.order_by(
                    Jornada.creado_en.desc(),
                    Jornada.fecha_jornada.desc()
                )
            else:
                # Por defecto: fecha descendente
                query_historial = query_historial.order_by(
                    Jornada.fecha_jornada.desc(),
                    Jornada.creado_en.desc()
                )
            
            # Aplicar límite si no se solicitan todos
            if not mostrar_todos:
                query_historial = query_historial.limit(20)
            
            jornadas_historial = query_historial.all()
            
            # Contar total de jornadas según el filtro aplicado
            try:
                if mostrar_todos_tipos:
                    # Si estamos mostrando todos, contar todos
                    total_jornadas = Jornada.query.count()
                elif mostrar_eliminados:
                    # Si estamos mostrando eliminados, contar solo eliminados
                    total_jornadas = Jornada.query.filter(Jornada.eliminado_en.isnot(None)).count()
                else:
                    # Si no, contar solo no eliminados
                    total_jornadas = Jornada.query.filter(Jornada.eliminado_en.is_(None)).count()
            except Exception as e:
                current_app.logger.warning(f"Error al contar total_jornadas: {e}")
                total_jornadas = len(jornadas_historial) if jornadas_historial else 0
        except Exception as e:
            current_app.logger.error(f"Error al obtener historial de jornadas: {e}", exc_info=True)
            jornadas_historial = []
            total_jornadas = 0
        
        # Calcular COSTO y RECAUDACION para cada jornada
        from app.models.pos_models import PosSale
        from sqlalchemy import func
        
        jornadas_con_datos = []
        for jornada in jornadas_historial:
            # Verificar que jornada no sea None
            if not jornada:
                current_app.logger.warning("⚠️ Jornada None encontrada en jornadas_historial, saltando")
                continue
            try:
                # Calcular COSTO: Suma de costo_total de todos los trabajadores de la planilla
                try:
                    costo_total = db.session.query(func.sum(PlanillaTrabajador.costo_total)).filter_by(
                        jornada_id=jornada.id
                    ).scalar() or 0.0
                except Exception as e:
                    current_app.logger.warning(f"Error al calcular costo para jornada {jornada.id}: {e}")
                    costo_total = 0.0
                
                # Calcular RECAUDACION: Suma de total_amount de todas las ventas del día de la jornada
                try:
                    recaudacion = db.session.query(func.sum(PosSale.total_amount)).filter(
                        PosSale.shift_date == jornada.fecha_jornada
                    ).scalar() or 0.0
                except Exception as e:
                    current_app.logger.warning(f"Error al calcular recaudación para jornada {jornada.id}: {e}")
                    recaudacion = 0.0
                
                # Obtener ENCARGADO: responsable_admin o abierto_por
                encargado = jornada.responsable_admin or jornada.abierto_por or 'Sin asignar'
                
                # Verificar que jornada no sea None antes de agregar
                if jornada:
                    jornadas_con_datos.append({
                        'jornada': jornada,
                        'costo_total': float(costo_total),
                        'recaudacion': float(recaudacion),
                        'encargado': encargado
                    })
                else:
                    current_app.logger.warning(f"⚠️ Jornada es None en el loop, saltando")
            except Exception as e:
                current_app.logger.error(f"Error al procesar jornada {jornada.id if jornada else 'None'}: {e}", exc_info=True)
                # Continuar con la siguiente jornada si hay error
                continue
        
        # Obtener empleados disponibles (para el JavaScript)
        empleados_disponibles = []
        try:
            from app.models.pos_models import Employee
            empleados_disponibles = Employee.query.filter_by(is_active=True).all()
        except Exception as e:
            current_app.logger.warning(f"No se pudieron cargar empleados: {e}")
            empleados_disponibles = []
        
        # Asegurar que todas las variables tengan valores por defecto seguros
        # (Ya están inicializadas arriba, pero por si acaso)
        if not isinstance(planilla_trabajadores, list):
            planilla_trabajadores = []
        if not isinstance(jornadas_historial, list):
            jornadas_historial = []
        if not isinstance(jornadas_con_datos, list):
            jornadas_con_datos = []
        if not isinstance(empleados_disponibles, list):
            empleados_disponibles = []
        
        # Todas las variables de filtro ya están definidas arriba, no necesitan validación adicional
        
        try:
            return render_template('admin_turnos.html',
                     jornada_actual=jornada_actual,
                     jornada=jornada_actual,  # Alias para compatibilidad
                     fecha_hoy=fecha_hoy,
                     planilla_trabajadores=planilla_trabajadores,
                     jornadas_historial=jornadas_historial,
                     jornadas_con_datos=jornadas_con_datos,  # Jornadas con costo y recaudación calculados
                     empleados_disponibles=empleados_disponibles,
                     filtro_estado=filtro_estado,
                     filtro_tipo=filtro_tipo,
                     filtro_fecha_desde=filtro_fecha_desde,
                     filtro_fecha_hasta=filtro_fecha_hasta,
                     ordenar_por=ordenar_por,
                     mostrar_todos=mostrar_todos,
                     mostrar_eliminados=mostrar_eliminados,
                     mostrar_todos_tipos=mostrar_todos_tipos,
                     total_jornadas=total_jornadas)
        except Exception as template_error:
            current_app.logger.error(f"❌ Error al renderizar template admin_turnos.html: {template_error}", exc_info=True)
            raise template_error
    except Exception as e:
        # Log del error con toda la información posible
        try:
            current_app.logger.error(f"❌ Error en admin_turnos: {e}", exc_info=True)
        except:
            try:
                import logging
                logging.error(f"Error en admin_turnos: {e}", exc_info=True)
            except:
                pass
        
        # Intentar redirigir al dashboard con mensaje de error
        # redirect, flash y url_for ya están importados al inicio del archivo
        try:
            flash(f"Error al cargar la página de turnos: {str(e)}", "error")
            return redirect(url_for('routes.admin_dashboard'))
        except Exception as redirect_error:
            # Si incluso el redirect falla, devolver un error HTTP básico
            try:
                from flask import render_template_string
                return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head><title>Error</title></head>
                    <body>
                        <h1>Error al cargar la página</h1>
                        <p>Hubo un error al cargar la página de turnos. Por favor, intenta nuevamente.</p>
                        <p><a href="/admin/dashboard">Volver al panel de control</a></p>
                    </body>
                    </html>
                """), 500
            except:
                return "Error al cargar la página de turnos", 500


@bp.route('/admin/jornada/crear', methods=['POST'])
def crear_jornada():
    """Crear una nueva jornada"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = JornadaService()
        request_dto = CrearJornadaRequest(
            fecha_jornada=request.form.get('fecha_jornada'),
            tipo_turno=request.form.get('tipo_turno'),
            nombre_fiesta=request.form.get('nombre_fiesta'),
            horario_apertura_programado=request.form.get('horario_apertura_programado'),
            # horario_cierre_programado y fecha_cierre_programada son opcionales
            # Se registrarán automáticamente al cerrar el turno
            horario_cierre_programado=None,
            fecha_cierre_programada=None,
            djs=request.form.get('djs', '')
        )
        
        success, message, jornada = service.crear_jornada(request_dto, session.get('admin_user', 'admin'))
        
        if success:
            flash(message, 'success')
            return redirect(url_for('routes.admin_turnos', jornada_id=jornada.id if jornada else None))
        else:
            flash(message, 'error')
            return redirect(url_for('routes.admin_turnos'))
    except Exception as e:
        flash(f'Error al crear jornada: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/actualizar', methods=['POST'])
def actualizar_jornada():
    """Actualizar una jornada existente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        jornada_id = request.form.get('jornada_id', type=int)
        if not jornada_id:
            flash('ID de jornada requerido', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            flash('Jornada no encontrada', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        # PERMITIR modificar turnos abiertos - registrar cambios para auditoría
        es_turno_abierto = jornada.estado_apertura == 'abierto'
        if es_turno_abierto:
            current_app.logger.warning(f"⚠️ Modificando turno ABIERTO (ID: {jornada_id}) - Los cambios se reflejarán en el cierre")
            flash('⚠️ Modificando turno abierto. Los cambios se reflejarán en el cierre del turno.', 'warning')
        
        # Actualizar campos - asegurar que todos los datos se guarden
        fecha_jornada = request.form.get('fecha_jornada')
        fecha_cierre = request.form.get('fecha_cierre_programada')
        tipo_turno = request.form.get('tipo_turno')
        nombre_fiesta = request.form.get('nombre_fiesta')
        horario_apertura = request.form.get('horario_apertura_programado')
        horario_cierre = request.form.get('horario_cierre_programado')
        djs = request.form.get('djs', '')
        
        # Validar que todos los campos requeridos estén presentes
        if fecha_jornada:
            jornada.fecha_jornada = fecha_jornada
        if fecha_cierre:
            jornada.fecha_cierre_programada = fecha_cierre
        elif horario_apertura and horario_cierre:
            # Calcular fecha_cierre automáticamente si no se proporciona
            from datetime import datetime, timedelta
            try:
                fecha_ap = datetime.strptime(jornada.fecha_jornada, '%Y-%m-%d')
                hora_ap_int = int(horario_apertura.split(':')[0])
                hora_ci_int = int(horario_cierre.split(':')[0])
                
                if hora_ci_int < hora_ap_int:
                    fecha_ci = fecha_ap + timedelta(days=1)
                else:
                    fecha_ci = fecha_ap
                
                jornada.fecha_cierre_programada = fecha_ci.strftime('%Y-%m-%d')
            except Exception as e:
                current_app.logger.warning(f"Error al calcular fecha_cierre: {e}")
        if tipo_turno:
            jornada.tipo_turno = tipo_turno
        if nombre_fiesta:
            jornada.nombre_fiesta = nombre_fiesta
        if horario_apertura:
            jornada.horario_apertura_programado = horario_apertura
        if horario_cierre:
            jornada.horario_cierre_programado = horario_cierre
        jornada.djs = djs
        
        # Log para debugging
        current_app.logger.info(f"💾 Actualizando jornada {jornada_id}:")
        current_app.logger.info(f"   Fecha: {jornada.fecha_jornada}")
        current_app.logger.info(f"   Tipo: {jornada.tipo_turno}")
        current_app.logger.info(f"   Nombre: {jornada.nombre_fiesta}")
        current_app.logger.info(f"   Horario: {jornada.horario_apertura_programado} - {jornada.horario_cierre_programado}")
        
        from app.models import db
        db.session.commit()
        
        # Verificar que se guardó correctamente
        jornada_verificada = Jornada.query.get(jornada_id)
        current_app.logger.info(f"✅ Jornada guardada en BD - Verificación:")
        current_app.logger.info(f"   Fecha: {jornada_verificada.fecha_jornada}")
        current_app.logger.info(f"   Tipo: {jornada_verificada.tipo_turno}")
        current_app.logger.info(f"   Nombre: {jornada_verificada.nombre_fiesta}")
        
        flash('Jornada actualizada correctamente', 'success')
        return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
    except Exception as e:
        flash(f'Error al actualizar jornada: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/asignar_planilla', methods=['POST'])
def asignar_planilla_responsables():
    """Guardar planilla de trabajadores"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener jornada_id del formulario
        jornada_id = request.form.get('jornada_id', type=int)
        
        # Log para debugging
        current_app.logger.info(f"📋 Guardando planilla - jornada_id recibido: {jornada_id}")
        current_app.logger.info(f"📋 Datos del formulario recibidos: {list(request.form.keys())}")
        
        if not jornada_id:
            current_app.logger.error("❌ No se recibió jornada_id en el formulario")
            flash('ID de jornada requerido. Asegúrate de haber creado el turno primero.', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        # Verificar que la jornada existe
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            current_app.logger.error(f"❌ Jornada con ID {jornada_id} no encontrada en la base de datos")
            flash('Jornada no encontrada. Por favor, crea el turno primero.', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        current_app.logger.info(f"✅ Jornada encontrada: ID={jornada.id}, Fecha={jornada.fecha_jornada}, Estado={jornada.estado_apertura}")
        
        # PERMITIR modificar planilla incluso si el turno está abierto
        # Esto permite agregar trabajadores olvidados o modificar asignaciones
        if jornada.estado_apertura == 'abierto':
            current_app.logger.warning(f"⚠️ Modificando planilla de turno ABIERTO (ID: {jornada_id}) - Los cambios se reflejarán en el cierre")
            flash('⚠️ Modificando planilla de turno abierto. Los cambios se reflejarán en el cierre del turno.', 'warning')
        
        # Obtener horarios de la jornada (turnos nocturnos cruzan medianoche)
        hora_inicio = jornada.horario_apertura_programado or '22:00'
        hora_fin = jornada.horario_cierre_programado or '05:00'
        
        # Obtener empleados disponibles para obtener nombres
        from app.models.pos_models import Employee
        empleados_dict = {str(emp.id): emp.name for emp in Employee.query.filter_by(is_active=True).all()}
        
        # Procesar datos del formulario con formato planilla[rowId][campo]
        planilla_data = {}
        keys_planilla = [k for k in request.form.keys() if k.startswith('planilla[')]
        current_app.logger.info(f"📋 Claves de planilla encontradas: {len(keys_planilla)}")
        
        for key in request.form.keys():
            if key.startswith('planilla[') and ']' in key:
                # Parsear planilla[rowId][campo]
                try:
                    # Extraer rowId y campo
                    parts = key.replace('planilla[', '').split('][')
                    if len(parts) == 2:
                        row_id = parts[0]
                        campo = parts[1].rstrip(']')
                        
                        if row_id not in planilla_data:
                            planilla_data[row_id] = {}
                        planilla_data[row_id][campo] = request.form.get(key)
                        current_app.logger.debug(f"📋 Parseado: {key} -> row_id={row_id}, campo={campo}, valor={request.form.get(key)}")
                except Exception as e:
                    current_app.logger.warning(f"Error parseando clave {key}: {e}")
                    continue
        
        current_app.logger.info(f"📋 Planilla procesada: {len(planilla_data)} filas encontradas")
        
        # CORRECCIÓN: Usar transacción atómica para asegurar consistencia
        from app.models.jornada_models import PlanillaTrabajador
        # db ya está importado al inicio del archivo
        
        try:
            # Validar que hay datos antes de procesar
            if not planilla_data:
                flash('No se recibieron datos de planilla. Verifica que hayas agregado trabajadores antes de guardar.', 'warning')
                return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
            
            # CONSULTA BD 1: Eliminar planilla anterior de esta jornada
            eliminados = PlanillaTrabajador.query.filter_by(jornada_id=jornada_id).delete()
            current_app.logger.info(f"🗑️ Planilla anterior eliminada: {eliminados} registro(s) para jornada {jornada_id}")
            
            # Guardar nueva planilla
            trabajadores_guardados = 0
            errores = []
            
            for row_id, datos in planilla_data.items():
                empleado_id = datos.get('empleado_id', '').strip()
                cargo = datos.get('cargo', '').strip()
                area = datos.get('area', cargo).strip() if datos.get('area') else cargo.strip()
                
                if not empleado_id or not cargo:
                    continue  # Saltar filas vacías
                
                # VALIDACIÓN: Verificar que no exista ya este trabajador en esta jornada
                trabajador_existente = PlanillaTrabajador.query.filter_by(
                    jornada_id=jornada_id,
                    id_empleado=empleado_id
                ).first()
                
                if trabajador_existente:
                    current_app.logger.warning(f"⚠️ Trabajador {empleado_id} ya está en la planilla de esta jornada. Se eliminará el registro anterior.")
                    # Eliminar el registro anterior (se reemplazará)
                    db.session.delete(trabajador_existente)
                
                # Obtener nombre del empleado desde el diccionario (ya cargado)
                nombre_empleado = empleados_dict.get(empleado_id, f'Empleado {empleado_id}')
                
                # CONSULTA BD 2: Obtener costo por hora del empleado (para compatibilidad con código existente)
                costo_hora = 0.0
                try:
                    if empleado_id.isdigit():
                        empleado = Employee.query.get(int(empleado_id))
                        if empleado:
                            # Intentar obtener costo_hora del empleado
                            if hasattr(empleado, 'costo_hora') and empleado.costo_hora:
                                costo_hora = float(empleado.costo_hora)
                            elif hasattr(empleado, 'salary') and empleado.salary:
                                costo_hora = float(empleado.salary) / 8.0
                            else:
                                # Si no tiene costo_hora, buscar por cargo en CargoSalaryConfig
                                from app.models.cargo_salary_models import CargoSalaryConfig
                                cargo_empleado = empleado.cargo or cargo
                                if cargo_empleado:
                                    config_cargo = CargoSalaryConfig.query.filter_by(cargo=cargo_empleado).first()
                                    if config_cargo and config_cargo.sueldo_por_turno:
                                        # Calcular costo por hora: sueldo por turno / horas del turno
                                        horas_turno = 8.0  # Por defecto 8 horas
                                        try:
                                            # Calcular horas reales del turno
                                            from datetime import datetime
                                            inicio = datetime.strptime(hora_inicio, '%H:%M')
                                            fin = datetime.strptime(hora_fin, '%H:%M')
                                            if fin < inicio:
                                                fin = fin.replace(day=fin.day + 1)
                                            diferencia = fin - inicio
                                            horas_turno = diferencia.total_seconds() / 3600.0
                                        except:
                                            pass
                                        costo_hora = float(config_cargo.sueldo_por_turno) / horas_turno if horas_turno > 0 else 0.0
                                        current_app.logger.info(f"💰 Costo/hora calculado desde cargo {cargo_empleado}: ${costo_hora:.2f} (sueldo: ${config_cargo.sueldo_por_turno}, horas: {horas_turno:.1f})")
                except Exception as e:
                    current_app.logger.warning(f"No se pudo obtener costo_hora para empleado {empleado_id}: {e}")
                    costo_hora = 0.0
                
                # Crear y guardar entrada en planilla
                try:
                    # Asegurar que todos los campos estén normalizados y ordenados
                    planilla_trabajador = PlanillaTrabajador(
                        jornada_id=jornada_id,
                        id_empleado=str(empleado_id).strip(),  # Normalizar ID
                        nombre_empleado=str(nombre_empleado).strip(),  # Normalizar nombre
                        rol=str(cargo).strip().upper(),  # Normalizar rol a mayúsculas para consistencia
                        hora_inicio=str(hora_inicio).strip(),  # Formato HH:MM
                        hora_fin=str(hora_fin).strip(),  # Formato HH:MM
                        costo_hora=float(costo_hora) if costo_hora else 0.0,  # Asegurar tipo numérico
                        area=str(area).strip() if area else str(cargo).strip().upper()  # Normalizar área
                    )
                    
                    # Calcular costo total (importante para estadísticas - compatibilidad con código existente)
                    planilla_trabajador.calcular_costo_total()
                    
                    # ⭐ NUEVO: CALCULAR Y CONGELAR PAGO AL MOMENTO DE ASIGNAR
                    # Esto congela sueldo_snapshot, bono_snapshot y pago_total
                    planilla_trabajador.calcular_y_congelar_pago(cargo_nombre=cargo)
                    
                    # CONSULTA BD 3: Agregar trabajador a la sesión
                    db.session.add(planilla_trabajador)
                    trabajadores_guardados += 1
                    
                except Exception as e:
                    error_msg = f"Error guardando {nombre_empleado}: {str(e)}"
                    errores.append(error_msg)
                    current_app.logger.error(f"Error guardando trabajador en planilla: {e}", exc_info=True)
                    continue
            
            # CONSULTA BD 4: Commit de toda la transacción
            db.session.commit()
            
            if trabajadores_guardados > 0:
                flash(f'✅ Planilla guardada correctamente en la base de datos. {trabajadores_guardados} trabajador(es) asignado(s).', 'success')
            else:
                flash('⚠️ No se guardaron trabajadores. Verifica que hayas seleccionado empleados y cargos antes de guardar.', 'warning')
            
            if errores:
                flash(f'⚠️ Algunos errores: {"; ".join(errores[:3])}', 'error')
                    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error en transacción al guardar planilla: {e}", exc_info=True)
            flash(f'❌ Error al guardar planilla en la base de datos: {str(e)}', 'error')
        
        return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al guardar planilla: {e}", exc_info=True)
        flash(f'Error al guardar planilla: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/planilla/agregar', methods=['POST'])
def api_agregar_trabajador_planilla():
    """API: Agregar trabajador a la planilla (persistencia inmediata)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
        
        jornada_id = data.get('jornada_id')
        if isinstance(jornada_id, str):
            jornada_id = int(jornada_id) if jornada_id.isdigit() else None
        else:
            jornada_id = int(jornada_id) if jornada_id else None
        
        cargo_id = data.get('cargo_id')
        if isinstance(cargo_id, str):
            cargo_id = int(cargo_id) if cargo_id.isdigit() else None
        else:
            cargo_id = int(cargo_id) if cargo_id else None
        
        trabajador_id = str(data.get('trabajador_id', '')).strip()
        origen = data.get('origen', 'manual')  # 'programacion' o 'manual'
        
        current_app.logger.info(f"📋 Agregar trabajador - jornada_id: {jornada_id}, cargo_id: {cargo_id}, trabajador_id: {trabajador_id}")
        
        if not jornada_id:
            return jsonify({'success': False, 'error': 'ID de jornada requerido'}), 400
        
        if not cargo_id or not trabajador_id:
            return jsonify({'success': False, 'error': 'Cargo y trabajador son requeridos'}), 400
        
        # Verificar que la jornada existe
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            return jsonify({'success': False, 'error': 'Jornada no encontrada'}), 404
        
        # Verificar que no esté cerrada (opcional, según requerimientos)
        if jornada.estado_apertura == 'cerrado':
            return jsonify({'success': False, 'error': 'No se puede modificar la planilla de un turno cerrado'}), 400
        
        # Obtener información del cargo
        from app.models.cargo_models import Cargo
        cargo = Cargo.query.get(cargo_id)
        if not cargo:
            return jsonify({'success': False, 'error': 'Cargo no encontrado'}), 404
        
        # Obtener información del trabajador
        from app.models.pos_models import Employee
        # Intentar buscar por ID (puede ser string o int)
        trabajador = Employee.query.get(trabajador_id)
        if not trabajador:
            # Intentar buscar por ID como string
            trabajador = Employee.query.filter_by(id=str(trabajador_id)).first()
        if not trabajador:
            current_app.logger.error(f"Trabajador no encontrado: ID={trabajador_id}, tipo={type(trabajador_id)}")
            # Listar algunos IDs disponibles para debugging
            algunos_ids = [str(e.id) for e in Employee.query.limit(5).all()]
            current_app.logger.info(f"IDs de trabajadores disponibles (primeros 5): {algunos_ids}")
            return jsonify({'success': False, 'error': f'Trabajador con ID "{trabajador_id}" no encontrado'}), 404
        
        # Verificar que no esté duplicado
        trabajador_existente = PlanillaTrabajador.query.filter_by(
            jornada_id=jornada_id,
            id_empleado=trabajador_id
        ).first()
        
        if trabajador_existente:
            return jsonify({'success': False, 'error': 'Este trabajador ya está en la planilla'}), 400
        
        # Obtener horarios de la jornada
        hora_inicio = jornada.horario_apertura_programado or '22:00'
        hora_fin = jornada.horario_cierre_programado or '05:00'
        
        # Calcular costo_hora (compatibilidad con código existente)
        costo_hora = 0.0
        try:
            from app.models.cargo_salary_models import CargoSalaryConfig
            config_cargo = CargoSalaryConfig.query.filter_by(cargo=cargo.nombre).first()
            if config_cargo and config_cargo.sueldo_por_turno:
                # Calcular horas del turno
                from datetime import datetime
                inicio = datetime.strptime(hora_inicio, '%H:%M')
                fin = datetime.strptime(hora_fin, '%H:%M')
                if fin < inicio:
                    fin = fin.replace(day=fin.day + 1)
                diferencia = fin - inicio
                horas_turno = diferencia.total_seconds() / 3600.0
                costo_hora = float(config_cargo.sueldo_por_turno) / horas_turno if horas_turno > 0 else 0.0
        except Exception as e:
            current_app.logger.warning(f"No se pudo calcular costo_hora: {e}")
        
        # Crear entrada en planilla
        planilla_trabajador = PlanillaTrabajador(
            jornada_id=jornada_id,
            id_empleado=str(trabajador_id).strip(),
            nombre_empleado=trabajador.name or f'Empleado {trabajador_id}',
            rol=cargo.nombre.upper(),
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            costo_hora=float(costo_hora) if costo_hora else 0.0,
            area=cargo.nombre.upper(),
            cargo_id=cargo_id,
            origen=origen
        )
        
        # Calcular costo total
        planilla_trabajador.calcular_costo_total()
        
        # Calcular y congelar pago
        planilla_trabajador.calcular_y_congelar_pago(cargo_nombre=cargo.nombre)
        
        # Guardar en BD
        db.session.add(planilla_trabajador)
        db.session.commit()
        
        current_app.logger.info(f"✅ Trabajador agregado a planilla: {planilla_trabajador.nombre_empleado} (origen: {origen})")
        
        return jsonify({
            'success': True,
            'message': 'Trabajador agregado correctamente',
            'planilla': planilla_trabajador.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al agregar trabajador a planilla: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/admin/jornada/planilla/<int:planilla_id>/eliminar', methods=['DELETE'])
def api_eliminar_trabajador_planilla(planilla_id):
    """API: Eliminar trabajador de la planilla"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        planilla_trabajador = PlanillaTrabajador.query.get(planilla_id)
        if not planilla_trabajador:
            return jsonify({'success': False, 'error': 'Registro de planilla no encontrado'}), 404
        
        # Verificar estado de la jornada
        jornada = Jornada.query.get(planilla_trabajador.jornada_id)
        if not jornada:
            return jsonify({'success': False, 'error': 'Jornada no encontrada'}), 404
        
        if jornada.estado_apertura == 'cerrado':
            return jsonify({'success': False, 'error': 'No se puede modificar la planilla de un turno cerrado'}), 400
        
        # Permitar eliminar incluso si está abierto (para correcciones durante el turno)
        
        nombre_trabajador = planilla_trabajador.nombre_empleado
        jornada_id = planilla_trabajador.jornada_id
        
        # Eliminar
        db.session.delete(planilla_trabajador)
        db.session.commit()
        
        current_app.logger.info(f"✅ Trabajador eliminado de planilla: {nombre_trabajador}")
        
        return jsonify({
            'success': True,
            'message': 'Trabajador eliminado correctamente',
            'jornada_id': jornada_id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar trabajador de planilla: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/admin/jornada/planilla/<int:jornada_id>/listar', methods=['GET'])
def api_listar_planilla(jornada_id):
    """API: Listar trabajadores de la planilla"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            return jsonify({'success': False, 'error': 'Jornada no encontrada'}), 404
        
        planilla_trabajadores = PlanillaTrabajador.query.filter_by(
            jornada_id=jornada_id
        ).order_by(
            PlanillaTrabajador.rol.asc(),
            PlanillaTrabajador.nombre_empleado.asc()
        ).all()
        
        return jsonify({
            'success': True,
            'planilla': [pt.to_dict() for pt in planilla_trabajadores],
            'total': len(planilla_trabajadores)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al listar planilla: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/admin/jornada/planilla/<int:planilla_id>/override_pago', methods=['POST'])
def override_pago_planilla(planilla_id):
    """
    Endpoint para hacer override del pago de un trabajador en la planilla.
    Solo disponible para admin/superadmin.
    Requiere motivo obligatorio.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        # Obtener datos del request
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        nuevo_sueldo = data.get('sueldo', type=float)
        nuevo_bono = data.get('bono', type=float)
        motivo = data.get('motivo', '').strip()
        
        # Validaciones
        if not motivo:
            return jsonify({'success': False, 'error': 'El motivo del override es obligatorio'}), 400
        
        if nuevo_sueldo is None or nuevo_sueldo < 0:
            return jsonify({'success': False, 'error': 'Sueldo inválido'}), 400
        
        if nuevo_bono is None or nuevo_bono < 0:
            nuevo_bono = 0.0
        
        # Obtener registro de planilla
        planilla_trabajador = PlanillaTrabajador.query.get_or_404(planilla_id)
        
        # Verificar que la jornada no esté cerrada (opcional, según requerimientos)
        jornada = Jornada.query.get(planilla_trabajador.jornada_id)
        if jornada and jornada.estado_apertura == 'cerrado':
            return jsonify({'success': False, 'error': 'No se puede modificar el pago de una jornada cerrada'}), 400
        
        # Guardar valores anteriores para auditoría
        sueldo_anterior = planilla_trabajador.sueldo_snapshot
        bono_anterior = planilla_trabajador.bono_snapshot
        total_anterior = planilla_trabajador.pago_total
        
        # Aplicar override
        planilla_trabajador.sueldo_snapshot = nuevo_sueldo
        planilla_trabajador.bono_snapshot = nuevo_bono
        planilla_trabajador.pago_total = nuevo_sueldo + nuevo_bono
        planilla_trabajador.override = True
        planilla_trabajador.override_motivo = motivo
        planilla_trabajador.override_por = session.get('admin_username', 'Admin')
        planilla_trabajador.override_en = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(
            f"✅ Override de pago aplicado por {planilla_trabajador.override_por} "
            f"para {planilla_trabajador.nombre_empleado}: "
            f"${sueldo_anterior}+${bono_anterior}=${total_anterior} → "
            f"${nuevo_sueldo}+${nuevo_bono}=${planilla_trabajador.pago_total} "
            f"(Motivo: {motivo})"
        )
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Pago actualizado correctamente',
                'planilla': planilla_trabajador.to_dict()
            })
        else:
            flash(f'✅ Pago actualizado para {planilla_trabajador.nombre_empleado}', 'success')
            return redirect(url_for('routes.admin_turnos', jornada_id=planilla_trabajador.jornada_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en override de pago: {e}", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error al actualizar pago: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/abrir_local', methods=['POST'])
def abrir_local():
    """Abrir el local (finalizar proceso de apertura)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        jornada_id = request.form.get('jornada_id', type=int)
        if not jornada_id:
            flash('ID de jornada requerido', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        service = JornadaService()
        request_dto = AbrirLocalRequest(
            abierto_por=session.get('admin_user', 'admin')
        )
        
        success, message = service.abrir_local(jornada_id, request_dto)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
    except Exception as e:
        flash(f'Error al abrir local: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/cerrar', methods=['POST'])
def cerrar_jornada():
    """Cerrar una jornada"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        jornada_id = request.form.get('jornada_id', type=int)
        if not jornada_id:
            flash('ID de jornada requerido', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            flash('Jornada no encontrada', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        from app.models import db
        from app.models.jornada_models import PlanillaTrabajador
        
        # IMPORTANTE: Obtener la planilla ACTUALIZADA (puede tener cambios realizados durante el turno abierto)
        planilla_actual = PlanillaTrabajador.query.filter_by(jornada_id=jornada_id).all()
        current_app.logger.info(f"📋 Cerrando jornada {jornada_id} con {len(planilla_actual)} trabajadores en la planilla")
        
        # Registrar que se está cerrando con la planilla actualizada
        for trabajador in planilla_actual:
            current_app.logger.info(f"   - {trabajador.nombre_empleado} ({trabajador.rol}): {trabajador.hora_inicio} - {trabajador.hora_fin} - Costo: ${trabajador.costo_total}")
        
        # Registrar hora de cierre real automáticamente
        now_chile = datetime.now(CHILE_TZ)
        now_local = now_chile.replace(tzinfo=None)
        hora_cierre_real = now_local.strftime('%H:%M')
        fecha_cierre_real = now_local.strftime('%Y-%m-%d')
        
        # Actualizar horario y fecha de cierre si no estaban registrados
        if not jornada.horario_cierre_programado:
            jornada.horario_cierre_programado = hora_cierre_real
        if not jornada.fecha_cierre_programada:
            jornada.fecha_cierre_programada = fecha_cierre_real
        
        jornada.estado_apertura = 'cerrado'
        # Nota: Si el modelo tiene cerrado_en y cerrado_por, se asignan; si no, se ignoran
        if hasattr(jornada, 'cerrado_en'):
            jornada.cerrado_en = now_local
        if hasattr(jornada, 'cerrado_por'):
            jornada.cerrado_por = session.get('admin_username', session.get('admin_user', 'admin'))
        
        current_app.logger.info(f"🕐 Turno cerrado a las {hora_cierre_real} del {fecha_cierre_real}")
        
        db.session.commit()
        
        # Enviar evento a n8n (después de commit exitoso)
        try:
            from app.helpers.n8n_client import send_shift_closed
            from app.models.delivery_models import Delivery
            from app.models.pos_models import PosSale
            
            # Calcular totales del turno
            shift_date = jornada.fecha_jornada.strftime('%Y-%m-%d') if hasattr(jornada.fecha_jornada, 'strftime') else str(jornada.fecha_jornada)
            
            # Contar entregas del día
            total_deliveries = Delivery.query.filter(
                db.func.date(Delivery.timestamp) == jornada.fecha_jornada
            ).count() if hasattr(jornada, 'fecha_jornada') else 0
            
            # Calcular total de ventas del día
            total_sales = 0.0
            try:
                sales = PosSale.query.filter(
                    db.func.date(PosSale.created_at) == jornada.fecha_jornada
                ).all() if hasattr(jornada, 'fecha_jornada') else []
                total_sales = sum(float(sale.total_amount or 0) for sale in sales)
            except:
                pass
            
            send_shift_closed(
                shift_date=shift_date,
                total_sales=total_sales,
                total_deliveries=total_deliveries
            )
        except Exception as e:
            current_app.logger.warning(f"Error enviando evento de cierre de turno a n8n: {e}")
        
        # Emitir actualización de métricas del dashboard
        try:
            from app import socketio
            from app.helpers.dashboard_metrics_service import get_metrics_service
            metrics_service = get_metrics_service()
            metrics = metrics_service.get_all_metrics(use_cache=False)
            socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
        except Exception as e:
            current_app.logger.warning(f"Error al emitir actualización de métricas: {e}")
        
        flash(f'Jornada cerrada correctamente. Planilla final: {len(planilla_actual)} trabajadores.', 'success')
        # Redirigir sin jornada_id para que los workflow steps se muestren limpios
        # El turno cerrado quedará en el historial pero no aparecerá como "jornada_actual"
        return redirect(url_for('routes.admin_turnos'))
    except Exception as e:
        flash(f'Error al cerrar jornada: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/eliminar', methods=['POST'])
def eliminar_jornada():
    """Eliminar una jornada (soft delete)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        jornada_id = request.form.get('jornada_id', type=int)
        razon_eliminacion = request.form.get('razon_eliminacion', '').strip()
        
        if not jornada_id:
            flash('ID de jornada requerido', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        if not razon_eliminacion or len(razon_eliminacion) < 10:
            flash('Debes proporcionar una explicación de al menos 10 caracteres', 'error')
            return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
        
        jornada = Jornada.query.get(jornada_id)
        if not jornada:
            flash('Jornada no encontrada', 'error')
            return redirect(url_for('routes.admin_turnos'))
        
        # Verificar que no esté ya eliminada
        if jornada.eliminado_en:
            flash('Este turno ya está eliminado', 'warning')
            return redirect(url_for('routes.admin_turnos'))
        
        # Verificar que no esté cerrado ni abierto
        if jornada.estado_apertura == 'cerrado':
            flash('No se puede eliminar un turno cerrado. Solo se pueden eliminar turnos en estado "preparando".', 'error')
            return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
        
        # Verificar que no esté abierto
        if jornada.estado_apertura == 'abierto':
            flash('No se puede eliminar un turno abierto. Debes cerrarlo primero antes de eliminarlo.', 'error')
            return redirect(url_for('routes.admin_turnos', jornada_id=jornada_id))
        
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        from app.models import db
        
        # Soft delete: marcar como eliminado pero no borrar
        jornada.eliminado_en = datetime.now(CHILE_TZ)
        jornada.eliminado_por = session.get('admin_username', session.get('admin_user', 'admin'))
        jornada.razon_eliminacion = razon_eliminacion
        
        db.session.commit()
        
        current_app.logger.info(f"✅ Turno {jornada_id} eliminado por {jornada.eliminado_por}. Razón: {razon_eliminacion}")
        flash(f'Turno eliminado correctamente. Razón: {razon_eliminacion}', 'success')
        return redirect(url_for('routes.admin_turnos'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar jornada: {e}", exc_info=True)
        flash(f'Error al eliminar turno: {str(e)}', 'error')
        return redirect(url_for('routes.admin_turnos'))


@bp.route('/admin/jornada/<int:jornada_id>/detalle')
def ver_detalle_jornada(jornada_id):
    """Ver detalle de una jornada"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    from app.models.jornada_models import PlanillaTrabajador
    from app.models import RegisterClose
    
    jornada = Jornada.query.get_or_404(jornada_id)
    
    # Obtener planilla de trabajadores
    planilla = PlanillaTrabajador.query.filter_by(
        jornada_id=jornada_id
    ).order_by(
        PlanillaTrabajador.rol.asc(),
        PlanillaTrabajador.nombre_empleado.asc()
    ).all()
    
    # Obtener cierres de caja relacionados con esta jornada
    cierres_caja = RegisterClose.query.filter_by(
        shift_date=jornada.fecha_jornada
    ).order_by(RegisterClose.closed_at.desc()).all()
    
    current_app.logger.info(f"📋 Detalle jornada {jornada_id}: {len(planilla)} trabajadores, {len(cierres_caja)} cierres")
    
    return render_template('admin_detalle_jornada.html', 
                         jornada=jornada,
                         planilla=planilla,
                         cierres_caja=cierres_caja)


@bp.route('/admin/scanner')
def admin_scanner():
    """Acceso directo al scanner para admin/superadmin"""
    if not session.get('admin_logged_in'):
        flash("Debes estar logueado como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    
    # Crear sesión automática de bartender para admin
    admin_username = session.get('admin_username', 'Admin')
    session['bartender'] = f"Admin: {admin_username}"
    session['bartender_id'] = f"admin-{admin_username.lower()}"
    session['bartender_first_name'] = admin_username
    session['bartender_last_name'] = 'Admin'
    session['is_admin_session'] = True  # Marcar como sesión de admin
    
    # Si no hay barra seleccionada, usar una por defecto
    if 'barra' not in session:
        session['barra'] = 'Barra Principal'
    
    # Redirigir al scanner
    return redirect(url_for('scanner.scanner'))
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return redirect(url_for('scanner.scanner'))


@bp.route('/admin/export/csv')
def export_csv():
    """Exportar logs en CSV"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return redirect(url_for('api.export_logs'))


@bp.route('/admin/fraud/config', methods=['GET', 'POST'])
def fraud_config():
    """Configuración de fraude"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    if request.method == 'POST':
        # Actualizar configuración
        try:
            from app.helpers.fraud_detection import load_fraud_config, save_fraud_config
            config = load_fraud_config()
            config['max_hours_old_ticket'] = int(request.form.get('max_hours_old_ticket', 24))
            config['max_attempts_per_hour'] = int(request.form.get('max_attempts_per_hour', 10))
            save_fraud_config(config)
            flash('Configuración actualizada correctamente', 'success')
        except Exception as e:
            flash(f'Error al actualizar configuración: {str(e)}', 'error')
        return redirect(url_for('routes.fraud_config'))
    
    # GET - Mostrar configuración
    try:
        from app.helpers.fraud_detection import load_fraud_config, load_fraud_attempts
        config = load_fraud_config()
        attempts = load_fraud_attempts()
        total_fraud_attempts = len(attempts)
        authorized_count = sum(1 for a in attempts if len(a) > 7 and a[7] == '1')
        unauthorized_count = total_fraud_attempts - authorized_count
    except Exception as e:
        config = {'max_hours_old_ticket': 24, 'max_attempts_per_hour': 10}
        total_fraud_attempts = 0
        authorized_count = 0
        unauthorized_count = 0
    
    return render_template('admin_fraud_config.html',
                         config=config,
                         total_fraud_attempts=total_fraud_attempts,
                         authorized_count=authorized_count,
                         unauthorized_count=unauthorized_count)


@bp.route('/admin/fraud/history')
def fraud_history():
    """Historial de fraudes"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.helpers.fraud_detection import load_fraud_attempts
        attempts = load_fraud_attempts()
    except Exception:
        attempts = []
    
    return render_template('admin_fraud_history.html', fraud_attempts=attempts)


@bp.route('/admin/apertura')
def apertura():
    """Página de apertura"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin/apertura_cierre.html')


@bp.route('/admin/shift/open', methods=['GET', 'POST'])
def open_shift():
    """Abrir turno"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Si es POST, procesar la apertura del turno
    if request.method == 'POST':
        try:
            from app.helpers.shift_manager_compat import open_shift as open_shift_func
            from datetime import datetime
            from app.utils.timezone import CHILE_TZ
            
            # Obtener datos del formulario
            fiesta_nombre = request.form.get('fiesta_nombre', '').strip()
            djs = request.form.getlist('djs')  # Lista de DJs
            djs_str = ', '.join([dj for dj in djs if dj.strip()]) if djs else ''
            barras_disponibles = request.form.getlist('barras_disponibles')
            bartenders = request.form.getlist('bartenders')
            opened_by = session.get('admin_username', 'admin')
            
            # Validar que se haya proporcionado el nombre de la fiesta
            if not fiesta_nombre:
                flash('El nombre de la fiesta es requerido', 'error')
                return render_template('admin/open_shift.html')
            
            # Abrir el turno usando el sistema de jornadas
            success, message = open_shift_func(
                fiesta_nombre=fiesta_nombre,
                djs=djs_str,
                barras_disponibles=barras_disponibles if barras_disponibles else None,
                bartenders=bartenders if bartenders else None,
                opened_by=opened_by
            )
            
            if success:
                flash(f'✅ {message}', 'success')
                return redirect(url_for('routes.admin_dashboard'))
            else:
                flash(f'❌ {message}', 'error')
                return render_template('admin/open_shift.html')
                
        except Exception as e:
            current_app.logger.error(f"Error al abrir turno: {e}", exc_info=True)
            flash(f'Error al abrir turno: {str(e)}', 'error')
            return render_template('admin/open_shift.html')
    
    # Si es GET, mostrar el formulario
    return render_template('admin/open_shift.html')


@bp.route('/admin/shift/close', methods=['POST'])
def close_shift():
    """Cerrar turno"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Lógica para cerrar turno
        flash('Turno cerrado correctamente', 'success')
    except Exception as e:
        flash(f'Error al cerrar turno: {str(e)}', 'error')
    
    return redirect(url_for('home.index'))


@bp.route('/admin/shift/history')
def shift_history():
    """Historial de turnos"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin/shift_history.html')


@bp.route('/admin/inventario')
@bp.route('/admin/inventory/view')
@bp.route('/admin/inventory')
def view_inventory():
    """Redirigir a la nueva vista mejorada de inventario"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    return redirect(url_for('inventory_admin.dashboard'))
    """Ver inventario - Gestión de productos organizados por categoría"""
    if not session.get('admin_logged_in'):
        current_app.logger.warning(f"⚠️ Intento de acceso a /admin/inventario sin autenticación")
        return redirect(url_for('auth.login_admin'))
    
    current_app.logger.info(f"✅ Accediendo a /admin/inventario - usuario: {session.get('admin_username', 'unknown')}")
    try:
        from app.models.product_models import Product
        from sqlalchemy import func
        
        # Obtener todos los productos activos organizados por categoría
        productos_por_categoria = {}
        productos_sin_categoria = []
        
        # Obtener productos agrupados por categoría
        productos = Product.query.filter_by(is_active=True).order_by(Product.category, Product.name).all()
        
        for producto in productos:
            categoria = producto.category or 'Sin Categoría'
            if categoria == 'Sin Categoría':
                productos_sin_categoria.append(producto)
            else:
                if categoria not in productos_por_categoria:
                    productos_por_categoria[categoria] = []
                productos_por_categoria[categoria].append(producto)
        
        # Si hay productos sin categoría, agregarlos al final
        if productos_sin_categoria:
            productos_por_categoria['Sin Categoría'] = productos_sin_categoria
        
        # Estadísticas
        total_productos = len(productos)
        total_categorias = len(productos_por_categoria)
        
        # Obtener fecha del turno actual si existe
        from app.models.jornada_models import Jornada
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        fecha_hoy = datetime.now(CHILE_TZ).date()
        jornada_abierta = Jornada.query.filter_by(
            fecha_jornada=fecha_hoy,
            estado_apertura='abierto',
            eliminado_en=None
        ).order_by(Jornada.fecha_jornada.desc()).first()
        
        shift_date = jornada_abierta.fecha_jornada if jornada_abierta else fecha_hoy
        
        # Verificar qué productos tienen recetas
        from app.models.inventory_stock_models import Recipe
        productos_con_receta = {r.product_id for r in Recipe.query.filter_by(is_active=True).all()}
        
        def recipe_exists(product_id):
            return product_id in productos_con_receta
        
        return render_template(
            'admin/inventory.html',
            productos_por_categoria=productos_por_categoria,
            total_productos=total_productos,
            total_categorias=total_categorias,
            shift_date=shift_date,
            recipe_exists=recipe_exists
        )
    except Exception as e:
        current_app.logger.error(f"❌ Error al renderizar inventory.html: {e}", exc_info=True)
        flash(f'Error al cargar inventario: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))

@bp.route('/admin/inventory/finalize', methods=['POST'])
def finalize_inventory():
    """Finalizar inventario"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        barra = request.form.get('barra')
        # Lógica para finalizar inventario
        return jsonify({'success': True, 'message': 'Inventario finalizado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500




@bp.route('/admin/inventory/register', methods=['GET', 'POST'])
def register_inventory():
    """Registrar inventario"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Barras disponibles
    barras_disponibles = ['Barra Pista', 'Terraza']
    
    if request.method == 'POST':
        try:
            # Lógica para registrar inventario
            flash('Inventario registrado correctamente', 'success')
            return redirect(url_for('routes.view_inventory'))
        except Exception as e:
            flash(f'Error al registrar inventario: {str(e)}', 'error')
    
    # Obtener productos para el datalist
    from app.models.product_models import Product
    all_products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    return render_template('admin/register_inventory.html', 
                         barras_disponibles=barras_disponibles,
                         all_products=all_products)


@bp.route('/admin/social_media')
def admin_social_media():
    """Gestión de redes sociales"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin_social_media.html')


@bp.route('/admin/service/restart', methods=['POST'])
def restart_service():
    """Reiniciar servicio"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        # Lógica para reiniciar servicio (si es necesario)
        return jsonify({'success': True, 'message': 'Servicio reiniciado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/admin/pagos/generar')
def admin_generar_pagos():
    """Generar pagos"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin/generar_pagos.html')


@bp.route('/admin/programacion')
def admin_programacion():
    """Gestión de programación de eventos"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.application.services.programacion_service import ProgramacionService
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        from calendar import monthrange
        
        service = ProgramacionService()
        
        # Obtener año y mes de los parámetros o usar el actual
        año = request.args.get('año', type=int) or datetime.now(CHILE_TZ).year
        mes = request.args.get('mes', type=int) or datetime.now(CHILE_TZ).month
        
        # Validar mes
        if mes < 1 or mes > 12:
            mes = datetime.now(CHILE_TZ).month
        
        # Obtener eventos del mes
        eventos = service.get_eventos_mes(año, mes)
        
        # Obtener evento de hoy si existe
        evento_hoy = service.get_evento_hoy()
        
        # Fecha de hoy
        fecha_hoy = datetime.now(CHILE_TZ).date()
        
        # Calcular días del mes
        _, dias_mes = monthrange(año, mes)
        
        # Obtener el primer día del mes para calcular el offset
        primer_dia = datetime(año, mes, 1).date()
        dia_semana_inicio = primer_dia.weekday()  # 0 = Lunes, 6 = Domingo
        
        # Crear calendario con eventos
        calendario = []
        
        # Agregar días vacíos al inicio si el mes no comienza en lunes
        for _ in range(dia_semana_inicio):
            calendario.append({
                'dia': None,
                'fecha': None,
                'evento': None
            })
        
        # Agregar días del mes
        for dia in range(1, dias_mes + 1):
            fecha = datetime(año, mes, dia).date()
            evento_dia = next((e for e in eventos if e.fecha == fecha), None)
            calendario.append({
                'dia': dia,
                'fecha': fecha,
                'evento': evento_dia
            })
        
        # Meses en español
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        return render_template(
            'admin/programacion.html',
            eventos=eventos,
            evento_hoy=evento_hoy,
            calendario=calendario,
            año=año,
            mes=mes,
            nombre_mes=meses[mes - 1],
            dias_mes=dias_mes,
            fecha_hoy=fecha_hoy
        )
    except Exception as e:
        current_app.logger.error(f"Error al cargar programación: {e}", exc_info=True)
        flash(f'Error al cargar programación: {str(e)}', 'error')
        return render_template('admin/programacion.html', eventos=[], calendario=[])


@bp.route('/admin/programacion/crear', methods=['GET', 'POST'])
def admin_programacion_crear():
    """Crear nuevo evento"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    if request.method == 'POST':
        try:
            from app.application.services.programacion_service import ProgramacionService
            from datetime import datetime
            
            service = ProgramacionService()
            
            # Recopilar datos del formulario
            datos = {
                'fecha': request.form.get('fecha'),
                'nombre_evento': request.form.get('nombre_evento', '').strip(),
                'tipo_noche': request.form.get('tipo_noche', '').strip() or None,
                'dj_principal': request.form.get('dj_principal', '').strip() or None,
                'otros_djs': request.form.get('otros_djs', '').strip() or None,
                'estilos_musica': request.form.get('estilos_musica', '').strip() or None,
                'horario_apertura_publico': request.form.get('horario_apertura_publico') or None,
                'horario_cierre_publico': request.form.get('horario_cierre_publico') or None,
                'info_lista': request.form.get('info_lista', '').strip() or None,
                'descripcion_corta': request.form.get('descripcion_corta', '').strip() or None,
                'copy_ig_corto': request.form.get('copy_ig_corto', '').strip() or None,
                'copy_whatsapp_corto': request.form.get('copy_whatsapp_corto', '').strip() or None,
                'hashtags_sugeridos': request.form.get('hashtags_sugeridos', '').strip() or None,
                'estado_publico': request.form.get('estado_publico', 'borrador'),
                'estado_produccion': request.form.get('estado_produccion', 'idea'),
                'dj_confirmado': request.form.get('dj_confirmado') == 'on',
                'cache_dj_principal': request.form.get('cache_dj_principal', type=float) or None,
                'cache_otros_djs': request.form.get('cache_otros_djs', type=float) or None,
                'costos_produccion_estimados': request.form.get('costos_produccion_estimados', type=float) or None,
                'presupuesto_marketing': request.form.get('presupuesto_marketing', type=float) or None,
                'ingresos_estimados': request.form.get('ingresos_estimados', type=float) or None,
                'aforo_objetivo': request.form.get('aforo_objetivo', type=int) or None,
                'notas_internas': request.form.get('notas_internas', '').strip() or None,
            }
            
            # Procesar precios (tiers)
            precios = []
            if request.form.get('precio_tier_1'):
                precios.append({
                    'tier': request.form.get('tier_nombre_1', 'General'),
                    'precio': request.form.get('precio_tier_1', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_1') or None
                })
            if request.form.get('precio_tier_2'):
                precios.append({
                    'tier': request.form.get('tier_nombre_2', 'Late'),
                    'precio': request.form.get('precio_tier_2', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_2') or None
                })
            if request.form.get('precio_tier_3'):
                precios.append({
                    'tier': request.form.get('tier_nombre_3', 'VIP'),
                    'precio': request.form.get('precio_tier_3', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_3') or None
                })
            datos['precios'] = precios if precios else None
            
            creado_por = session.get('admin_username', session.get('admin_user', 'admin'))
            evento = service.crear_evento(datos, creado_por)
            
            if evento:
                flash('Evento creado correctamente', 'success')
                return redirect(url_for('routes.admin_programacion', año=evento.fecha.year, mes=evento.fecha.month))
            else:
                flash('Error al crear evento', 'error')
        except Exception as e:
            current_app.logger.error(f"Error al crear evento: {e}", exc_info=True)
            flash(f'Error al crear evento: {str(e)}', 'error')
    
    # GET: Mostrar formulario
    fecha_predefinida = request.args.get('fecha')
    return render_template('admin/programacion_form.html', evento=None, fecha_predefinida=fecha_predefinida)


@bp.route('/admin/programacion/editar/<int:evento_id>', methods=['GET', 'POST'])
def admin_programacion_editar(evento_id):
    """Editar evento existente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    from app.models.programacion_models import ProgramacionEvento
    
    evento = ProgramacionEvento.query.get_or_404(evento_id)
    
    if request.method == 'POST':
        try:
            from app.application.services.programacion_service import ProgramacionService
            
            service = ProgramacionService()
            
            # Recopilar datos del formulario
            datos = {
                'fecha': request.form.get('fecha'),
                'nombre_evento': request.form.get('nombre_evento', '').strip(),
                'tipo_noche': request.form.get('tipo_noche', '').strip() or None,
                'dj_principal': request.form.get('dj_principal', '').strip() or None,
                'otros_djs': request.form.get('otros_djs', '').strip() or None,
                'estilos_musica': request.form.get('estilos_musica', '').strip() or None,
                'horario_apertura_publico': request.form.get('horario_apertura_publico') or None,
                'horario_cierre_publico': request.form.get('horario_cierre_publico') or None,
                'info_lista': request.form.get('info_lista', '').strip() or None,
                'descripcion_corta': request.form.get('descripcion_corta', '').strip() or None,
                'copy_ig_corto': request.form.get('copy_ig_corto', '').strip() or None,
                'copy_whatsapp_corto': request.form.get('copy_whatsapp_corto', '').strip() or None,
                'hashtags_sugeridos': request.form.get('hashtags_sugeridos', '').strip() or None,
                'estado_publico': request.form.get('estado_publico', 'borrador'),
                'estado_produccion': request.form.get('estado_produccion', 'idea'),
                'dj_confirmado': request.form.get('dj_confirmado') == 'on',
                'cache_dj_principal': request.form.get('cache_dj_principal', type=float) or None,
                'cache_otros_djs': request.form.get('cache_otros_djs', type=float) or None,
                'costos_produccion_estimados': request.form.get('costos_produccion_estimados', type=float) or None,
                'presupuesto_marketing': request.form.get('presupuesto_marketing', type=float) or None,
                'ingresos_estimados': request.form.get('ingresos_estimados', type=float) or None,
                'aforo_objetivo': request.form.get('aforo_objetivo', type=int) or None,
                'notas_internas': request.form.get('notas_internas', '').strip() or None,
            }
            
            # Procesar precios (tiers)
            precios = []
            if request.form.get('precio_tier_1'):
                precios.append({
                    'tier': request.form.get('tier_nombre_1', 'General'),
                    'precio': request.form.get('precio_tier_1', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_1') or None
                })
            if request.form.get('precio_tier_2'):
                precios.append({
                    'tier': request.form.get('tier_nombre_2', 'Late'),
                    'precio': request.form.get('precio_tier_2', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_2') or None
                })
            if request.form.get('precio_tier_3'):
                precios.append({
                    'tier': request.form.get('tier_nombre_3', 'VIP'),
                    'precio': request.form.get('precio_tier_3', type=float) or 0,
                    'hasta': request.form.get('tier_hasta_3') or None
                })
            datos['precios'] = precios if precios else None
            
            actualizado_por = session.get('admin_username', session.get('admin_user', 'admin'))
            evento_actualizado = service.actualizar_evento(evento_id, datos, actualizado_por)
            
            if evento_actualizado:
                flash('Evento actualizado correctamente', 'success')
                return redirect(url_for('routes.admin_programacion', año=evento_actualizado.fecha.year, mes=evento_actualizado.fecha.month))
            else:
                flash('Error al actualizar evento', 'error')
        except Exception as e:
            current_app.logger.error(f"Error al actualizar evento: {e}", exc_info=True)
            flash(f'Error al actualizar evento: {str(e)}', 'error')
    
    # GET: Mostrar formulario con datos del evento
    return render_template('admin/programacion_form.html', evento=evento, fecha_predefinida=None)


@bp.route('/admin/programacion/eliminar/<int:evento_id>', methods=['POST'])
def admin_programacion_eliminar(evento_id):
    """Eliminar evento (soft delete)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.models.programacion_models import ProgramacionEvento
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        evento = ProgramacionEvento.query.get_or_404(evento_id)
        
        evento.eliminado_en = datetime.now(CHILE_TZ)
        evento.eliminado_por = session.get('admin_username', session.get('admin_user', 'admin'))
        
        db.session.commit()
        
        flash('Evento eliminado correctamente', 'success')
        return redirect(url_for('routes.admin_programacion', año=evento.fecha.year, mes=evento.fecha.month))
    except Exception as e:
        current_app.logger.error(f"Error al eliminar evento: {e}", exc_info=True)
        flash(f'Error al eliminar evento: {str(e)}', 'error')
        return redirect(url_for('routes.admin_programacion'))


@bp.route('/admin/programacion/preview', methods=['POST'])
def admin_programacion_preview():
    """
    Previsualiza la importación de asignaciones de personal sin guardar.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        from app.application.services.programacion_personal_service import ProgramacionPersonalService
        from datetime import datetime
        
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        texto = data.get('texto', '').strip()
        fecha_viernes_str = data.get('fecha_viernes', '')
        fecha_sabado_str = data.get('fecha_sabado', '')
        tipo_turno = data.get('tipo_turno', 'NOCHE').upper()
        
        # Validaciones
        if not texto:
            return jsonify({'success': False, 'error': 'El texto está vacío'}), 400
        
        if not fecha_viernes_str or not fecha_sabado_str:
            return jsonify({'success': False, 'error': 'Fechas requeridas'}), 400
        
        if tipo_turno not in ['NOCHE', 'DIA']:
            return jsonify({'success': False, 'error': 'Tipo de turno debe ser NOCHE o DIA'}), 400
        
        # Parsear fechas
        try:
            fecha_viernes = datetime.strptime(fecha_viernes_str, '%Y-%m-%d').date()
            fecha_sabado = datetime.strptime(fecha_sabado_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400
        
        # Previsualizar
        service = ProgramacionPersonalService()
        resultados = service.previsualizar_importacion(
            texto=texto,
            fecha_viernes=fecha_viernes,
            fecha_sabado=fecha_sabado,
            tipo_turno=tipo_turno
        )
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'resumen': {
                'validos': len(resultados['validos']),
                'errores': len(resultados['errores']),
                'advertencias': len(resultados['advertencias'])
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en preview de importación: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/admin/programacion/import', methods=['POST'])
def admin_programacion_import():
    """
    Importa asignaciones de personal desde texto copiado de tabla.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        from app.application.services.programacion_personal_service import ProgramacionPersonalService
        from datetime import datetime
        
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        texto = data.get('texto', '').strip()
        fecha_viernes_str = data.get('fecha_viernes', '')
        fecha_sabado_str = data.get('fecha_sabado', '')
        tipo_turno = data.get('tipo_turno', 'NOCHE').upper()
        crear_placeholders = data.get('crear_placeholders', False)
        
        # Validaciones
        if not texto:
            return jsonify({'success': False, 'error': 'El texto está vacío'}), 400
        
        if not fecha_viernes_str or not fecha_sabado_str:
            return jsonify({'success': False, 'error': 'Fechas requeridas'}), 400
        
        if tipo_turno not in ['NOCHE', 'DIA']:
            return jsonify({'success': False, 'error': 'Tipo de turno debe ser NOCHE o DIA'}), 400
        
        # Parsear fechas
        try:
            fecha_viernes = datetime.strptime(fecha_viernes_str, '%Y-%m-%d').date()
            fecha_sabado = datetime.strptime(fecha_sabado_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400
        
        # Importar
        service = ProgramacionPersonalService()
        resultados = service.importar_asignaciones(
            texto=texto,
            fecha_viernes=fecha_viernes,
            fecha_sabado=fecha_sabado,
            tipo_turno=tipo_turno,
            crear_placeholders=crear_placeholders
        )
        
        # Commit final
        db.session.commit()
        
        current_app.logger.info(
            f"✅ Importación de programación: {resultados['insertados']} insertados, "
            f"{resultados['duplicados']} duplicados, {len(resultados['errores'])} errores"
        )
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'resumen': {
                'insertados': resultados['insertados'],
                'duplicados': resultados['duplicados'],
                'errores': len(resultados['errores']),
                'advertencias': len(resultados['advertencias'])
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en importación de programación: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# Las rutas del bot de IA ahora están en app/blueprints/admin/bot_routes.py
# Se eliminaron las redirecciones para evitar bucles de redirección


@bp.route('/admin/logs/turno')
def admin_logs_turno():
    """Logs por turno"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    return render_template('admin_logs_turno.html',
                         current_page=page,
                         per_page=per_page)


@bp.route('/admin/logs/modulos')
def admin_logs_modulos():
    """Logs por módulos"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin_logs_modulos.html')


@bp.route('/admin/logs/pendientes')
def admin_logs_pendientes():
    """Logs pendientes"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    return render_template('admin_logs_pendientes.html')


# ========== API ENDPOINTS PARA ADMIN ==========

@bp.route('/admin/api/dashboard/metrics')
def api_dashboard_metrics():
    """API: Obtener todas las métricas del dashboard"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.dashboard_metrics_service import get_metrics_service
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_all_metrics(use_cache=False)  # Sin caché para API
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        current_app.logger.error(f"Error en api_dashboard_metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/register-sales-monitor')
def api_register_sales_monitor():
    """API: Obtener estadísticas de ventas por caja"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.register_sales_monitor import get_sales_by_register
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'
        
        data = get_sales_by_register()
        
        if include_stats:
            # Agregar estadísticas adicionales si se solicitan
            summary = data.get('summary', {})
            data['stats'] = {
                'total_registers': summary.get('total_registers', 0),
                'total_sales': summary.get('total_sales', 0),
                'total_amount': summary.get('total_amount', 0.0),
                'total_cash': summary.get('total_cash', 0.0),
                'total_debit': summary.get('total_debit', 0.0),
                'total_credit': summary.get('total_credit', 0.0)
            }
        
        response_data = {
            'success': True,
            'registers': data.get('registers', {}),
            'summary': data.get('summary', {})
        }
        
        if include_stats:
            response_data['stats'] = data.get('stats', {})
        
        return jsonify(response_data)
    except Exception as e:
        current_app.logger.error(f"Error en register-sales-monitor: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener estadísticas: {str(e)}'
        }), 500


@bp.route('/admin/api/register-closes')
def api_register_closes():
    """API: Obtener lista de cierres de caja"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.models import RegisterClose
        from sqlalchemy import desc
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        closes = RegisterClose.query.order_by(desc(RegisterClose.closed_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        closes_list = []
        for close in closes.items:
            closes_list.append({
                'id': close.id,
                'register_id': close.register_id,
                'register_name': close.register_name or f"Caja {close.register_id}",
                'employee_id': close.employee_id,
                'employee_name': close.employee_name,
                'shift_date': close.shift_date.strftime('%Y-%m-%d') if close.shift_date and hasattr(close.shift_date, 'strftime') else (str(close.shift_date) if close.shift_date else None),
                'opened_at': close.opened_at.isoformat() if close.opened_at and hasattr(close.opened_at, 'isoformat') else (str(close.opened_at) if close.opened_at else None),
                'closed_at': close.closed_at.isoformat() if close.closed_at and hasattr(close.closed_at, 'isoformat') else (str(close.closed_at) if close.closed_at else None),
                'expected_cash': float(close.expected_cash or 0),
                'actual_cash': float(close.actual_cash or 0),
                'diff_cash': float(close.diff_cash or 0),
                'expected_debit': float(close.expected_debit or 0),
                'actual_debit': float(close.actual_debit or 0),
                'diff_debit': float(close.diff_debit or 0),
                'expected_credit': float(close.expected_credit or 0),
                'actual_credit': float(close.actual_credit or 0),
                'diff_credit': float(close.diff_credit or 0),
                'total_amount': float(close.total_amount or 0),
                'difference_total': float(close.difference_total or 0),
                'notes': close.notes
            })
        
        return jsonify({
            'success': True,
            'closes': closes_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': closes.total,
                'pages': closes.pages,
                'has_prev': closes.has_prev,
                'has_next': closes.has_next
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error en register-closes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener cierres: {str(e)}'
        }), 500


@bp.route('/admin/api/pending-closes')
def api_pending_closes():
    """API: Obtener lista de cierres de caja pendientes"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.models import RegisterClose
        from datetime import datetime
        
        # Obtener cierres que no han sido aceptados (pendientes de revisión)
        closes = RegisterClose.query.filter_by(
            status='pending'
        ).order_by(
            RegisterClose.closed_at.desc()
        ).limit(10).all()
        
        pending_closes = []
        for close in closes:
            # Formatear fechas
            opened_at_formatted = None
            closed_at_formatted = None
            if close.opened_at:
                if hasattr(close.opened_at, 'strftime'):
                    opened_at_formatted = close.opened_at.strftime('%d/%m/%Y %H:%M')
                else:
                    opened_at_formatted = str(close.opened_at)
            if close.closed_at:
                if hasattr(close.closed_at, 'strftime'):
                    closed_at_formatted = close.closed_at.strftime('%d/%m/%Y %H:%M')
                else:
                    closed_at_formatted = str(close.closed_at)
            
            pending_closes.append({
                'id': close.id,
                'register_id': close.register_id,
                'register_name': close.register_name or f"Caja {close.register_id}",
                'employee_id': close.employee_id,
                'employee_name': close.employee_name,
                'shift_date': close.shift_date.strftime('%Y-%m-%d') if close.shift_date and hasattr(close.shift_date, 'strftime') else (str(close.shift_date) if close.shift_date else None),
                'opened_at': close.opened_at.isoformat() if close.opened_at and hasattr(close.opened_at, 'isoformat') else (str(close.opened_at) if close.opened_at else None),
                'opened_at_formatted': opened_at_formatted,
                'closed_at': close.closed_at.isoformat() if close.closed_at and hasattr(close.closed_at, 'isoformat') else (str(close.closed_at) if close.closed_at else None),
                'closed_at_formatted': closed_at_formatted,
                'expected_cash': float(close.expected_cash or 0),
                'actual_cash': float(close.actual_cash or 0),
                'diff_cash': float(close.diff_cash or 0),
                'expected_debit': float(close.expected_debit or 0),
                'actual_debit': float(close.actual_debit or 0),
                'diff_debit': float(close.diff_debit or 0),
                'expected_credit': float(close.expected_credit or 0),
                'actual_credit': float(close.actual_credit or 0),
                'diff_credit': float(close.diff_credit or 0),
                'total_amount': float(close.total_amount or 0),
                'difference_total': float(close.difference_total or 0),
                'notes': close.notes or ''
            })
        
        return jsonify({
            'success': True,
            'pending_closes': pending_closes
        })
    except Exception as e:
        current_app.logger.error(f"Error en pending-closes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener cierres pendientes: {str(e)}'
        }), 500


@bp.route('/admin/api/register-close/<int:close_id>')
def api_register_close_detail(close_id):
    """API: Obtener detalle de un cierre de caja específico"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.models import RegisterClose
        
        close = RegisterClose.query.get_or_404(close_id)
        
        return jsonify({
            'success': True,
            'close': {
                'id': close.id,
                'register_id': close.register_id,
                'register_name': close.register_name or f"Caja {close.register_id}",
                'employee_id': close.employee_id,
                'employee_name': close.employee_name,
                'shift_date': close.shift_date.strftime('%Y-%m-%d') if close.shift_date and hasattr(close.shift_date, 'strftime') else (str(close.shift_date) if close.shift_date else None),
                'opened_at': close.opened_at.isoformat() if close.opened_at and hasattr(close.opened_at, 'isoformat') else (str(close.opened_at) if close.opened_at else None),
                'closed_at': close.closed_at.isoformat() if close.closed_at and hasattr(close.closed_at, 'isoformat') else (str(close.closed_at) if close.closed_at else None),
                'expected_cash': float(close.expected_cash or 0),
                'actual_cash': float(close.actual_cash or 0),
                'diff_cash': float(close.diff_cash or 0),
                'expected_debit': float(close.expected_debit or 0),
                'actual_debit': float(close.actual_debit or 0),
                'diff_debit': float(close.diff_debit or 0),
                'expected_credit': float(close.expected_credit or 0),
                'actual_credit': float(close.actual_credit or 0),
                'diff_credit': float(close.diff_credit or 0),
                'total_amount': float(close.total_amount or 0),
                'difference_total': float(close.difference_total or 0),
                'notes': close.notes
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error en register-close detail: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener detalle: {str(e)}'
        }), 500


@bp.route('/admin/area')
def admin_area():
    """Área administrativa (alias de admin_logs)"""
    return redirect(url_for('routes.admin_logs'))


@bp.route('/admin/api/services/status')
def admin_api_services_status():
    """API: Obtener estado de todos los servicios"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.service_status import get_all_services_status
        
        services_status = get_all_services_status()
        
        # Agregar servicios adicionales que el template espera
        additional_services = {
            'openai': {
                'enabled': current_app.config.get('OPENAI_ENABLED', False),
                'name': 'OpenAI',
                'status': 'unknown',
                'running': None,
                'message': 'Servicio de OpenAI'
            }
        }
        
        # Combinar servicios del sistema con servicios adicionales
        all_services = {**services_status, **additional_services}
        
        return jsonify({
            'success': True,
            'services': all_services
        })
    except Exception as e:
        current_app.logger.error(f"Error en admin_api_services_status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/services/toggle', methods=['POST'])
def admin_api_services_toggle():
    """API: Activar/desactivar un servicio"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        service_name = data.get('service')
        enabled = data.get('enabled', False)
        
        # Solo permitir toggle de servicios válidos
        if service_name == 'openai':
            # Actualizar configuración de OpenAI
            current_app.config['OPENAI_ENABLED'] = enabled
            # TODO: Guardar en base de datos o archivo de configuración si es necesario
        
        return jsonify({
            'success': True,
            'message': f'Servicio {service_name} {"activado" if enabled else "desactivado"}'
        })
    except Exception as e:
        current_app.logger.error(f"Error en admin_api_services_toggle: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/services/configure', methods=['POST'])
def admin_api_services_configure():
    """API: Configurar un servicio"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        service = data.get('service')
        
        # Solo permitir configuración de servicios válidos
        if service == 'openai':
            # Actualizar configuración de OpenAI
            if 'api_key' in data:
                current_app.config['OPENAI_API_KEY'] = data['api_key']
            if 'org_id' in data:
                current_app.config['OPENAI_ORG_ID'] = data.get('org_id')
            if 'project_id' in data:
                current_app.config['OPENAI_PROJECT_ID'] = data.get('project_id')
            # TODO: Guardar en base de datos o archivo de configuración si es necesario
        
        return jsonify({
            'success': True,
            'message': f'Configuración de {service} guardada'
        })
    except Exception as e:
        current_app.logger.error(f"Error en admin_api_services_configure: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/n8n/config', methods=['GET'])
def admin_api_n8n_config_get():
    """API: Obtener configuración de n8n"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.models.system_config_models import SystemConfig
        
        # Obtener configuración desde SystemConfig, con fallback a variables de entorno
        webhook_url = SystemConfig.get('n8n_webhook_url') or os.environ.get('N8N_WEBHOOK_URL', '')
        webhook_secret = SystemConfig.get('n8n_webhook_secret') or os.environ.get('N8N_WEBHOOK_SECRET', '')
        api_key = SystemConfig.get('n8n_api_key') or os.environ.get('N8N_API_KEY', '')
        
        # Ocultar valores sensibles en la respuesta
        webhook_secret_display = webhook_secret[:8] + '...' if webhook_secret and len(webhook_secret) > 8 else (webhook_secret if webhook_secret else '')
        api_key_display = api_key[:8] + '...' if api_key and len(api_key) > 8 else (api_key if api_key else '')
        
        return jsonify({
            'success': True,
            'config': {
                'webhook_url': webhook_url,
                'webhook_secret': webhook_secret_display,
                'webhook_secret_set': bool(webhook_secret),
                'api_key': api_key_display,
                'api_key_set': bool(api_key),
                'enabled': bool(webhook_url)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error obteniendo configuración n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/n8n/config', methods=['POST'])
def admin_api_n8n_config_set():
    """API: Guardar configuración de n8n"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.models.system_config_models import SystemConfig
        from flask import session
        
        data = request.get_json()
        username = session.get('admin_username', 'admin')
        
        # Guardar configuración en SystemConfig
        if 'webhook_url' in data:
            webhook_url = data.get('webhook_url', '').strip()
            if webhook_url:
                SystemConfig.set(
                    'n8n_webhook_url',
                    webhook_url,
                    description='URL del webhook de n8n para recibir eventos',
                    updated_by=username
                )
            else:
                SystemConfig.delete('n8n_webhook_url')
        
        if 'webhook_secret' in data:
            webhook_secret = data.get('webhook_secret', '').strip()
            if webhook_secret:
                SystemConfig.set(
                    'n8n_webhook_secret',
                    webhook_secret,
                    description='Secreto para validar firmas de webhooks de n8n',
                    updated_by=username
                )
            else:
                SystemConfig.delete('n8n_webhook_secret')
        
        if 'api_key' in data:
            api_key = data.get('api_key', '').strip()
            if api_key:
                SystemConfig.set(
                    'n8n_api_key',
                    api_key,
                    description='API Key para autenticación con n8n',
                    updated_by=username
                )
            else:
                SystemConfig.delete('n8n_api_key')
        
        # Actualizar también en current_app.config para uso inmediato
        current_app.config['N8N_WEBHOOK_URL'] = SystemConfig.get('n8n_webhook_url') or os.environ.get('N8N_WEBHOOK_URL')
        current_app.config['N8N_WEBHOOK_SECRET'] = SystemConfig.get('n8n_webhook_secret') or os.environ.get('N8N_WEBHOOK_SECRET')
        current_app.config['N8N_API_KEY'] = SystemConfig.get('n8n_api_key') or os.environ.get('N8N_API_KEY')
        
        current_app.logger.info(f"Configuración de n8n actualizada por {username}")
        
        return jsonify({
            'success': True,
            'message': 'Configuración de n8n guardada correctamente'
        })
    except Exception as e:
        current_app.logger.error(f"Error guardando configuración n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/n8n/test', methods=['POST'])
def admin_api_n8n_test():
    """API: Probar conexión con n8n"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.n8n_client import send_to_n8n
        from datetime import datetime
        
        # Enviar evento de prueba (síncrono para obtener resultado inmediato)
        result = send_to_n8n('test', {
            'message': 'Prueba de conexión desde panel de control',
            'timestamp': datetime.utcnow().isoformat()
        }, async_mode=False, max_retries=1, timeout=5)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Conexión con n8n exitosa'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo conectar con n8n. Verifica la URL del webhook.'
            }), 400
    except Exception as e:
        current_app.logger.error(f"Error probando conexión n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/n8n/metrics', methods=['GET'])
def admin_api_n8n_metrics():
    """API: Obtener métricas de webhooks n8n"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.n8n_client import get_webhook_metrics
        
        metrics = get_webhook_metrics()
        
        # Calcular tasa de éxito
        total = metrics.get('total_sent', 0)
        success = metrics.get('total_success', 0)
        success_rate = (success / total * 100) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'metrics': {
                **metrics,
                'success_rate': round(success_rate, 2)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error obteniendo métricas n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/api/sync/start', methods=['POST'])
def admin_api_sync_start():
    """API: Iniciar sincronización de datos"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    # Verificar que NO estamos en producción
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    if is_production:
        return jsonify({
            'success': False,
            'error': 'La sincronización solo está disponible en el ambiente local. En producción no se usan archivos locales.'
        }), 400
    
    try:
        from app.helpers.sync_service import sync_all_data_async, is_sync_running
        
        if is_sync_running():
            return jsonify({
                'success': False,
                'error': 'Ya hay una sincronización en curso'
            }), 400
        
        result = sync_all_data_async()
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error al iniciar sincronización: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al iniciar sincronización: {str(e)}'
        }), 500


@bp.route('/admin/api/sync/status')
def admin_api_sync_status():
    """API: Obtener estado de la sincronización"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.sync_service import get_sync_status
        status = get_sync_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener estado de sincronización: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener estado: {str(e)}'
        }), 500


@bp.route('/admin/api/sync/tables')
def admin_api_sync_tables():
    """API: Obtener lista de tablas disponibles para sincronizar"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.helpers.sync_service import get_available_tables
        tables = get_available_tables()
        return jsonify({
            'success': True,
            'tables': tables
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener tablas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al obtener tablas: {str(e)}'
        }), 500


@bp.route('/admin/api/services/<service_name>/logs')
def admin_api_services_logs(service_name):
    """API: Obtener logs de un servicio"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    # Por ahora retornar logs vacíos
    return jsonify({
        'success': True,
        'logs': []
    })


@bp.route('/admin/api/deploy', methods=['POST'])
def admin_api_deploy():
    """API: Desplegar cambios a producción"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        import subprocess
        import os
        from threading import Thread
        from flask import copy_current_request_context
        
        # Verificar que gcloud esté disponible antes de iniciar el thread
        try:
            subprocess.run(
                ['gcloud', '--version'],
                check=True,
                timeout=5,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return jsonify({
                'success': False,
                'error': 'gcloud CLI no está instalado o no está disponible. El deployment solo funciona en servidores con gcloud configurado.'
            }), 400
        
        # Configuración de deployment para VM
        INSTANCE_NAME = "stvaldivia"
        ZONE = "southamerica-west1-a"
        PROJECT_ID = "stvaldivia"
        VM_IP = "34.176.144.166"
        
        # Función para ejecutar deployment en background
        @copy_current_request_context
        def run_deployment():
            try:
                # Script de deployment
                deploy_script = """
set -e
echo '🔄 Actualizando código...'
# Buscar directorio del proyecto (priorizar ubicaciones comunes)
PROJECT_DIR=""
for dir in /var/www/stvaldivia ~/tickets_cursor_clean ~/tickets ~/app ~/bimba; do
    if [ -d "$dir" ] && ([ -f "$dir/run_local.py" ] || [ -f "$dir/app.py" ] || [ -f "$dir/requirements.txt" ]); then
        PROJECT_DIR="$dir"
        break
    fi
done
if [ -z "$PROJECT_DIR" ]; then
    echo '⚠️  Directorio del proyecto no encontrado, buscando...'
    PROJECT_DIR=$(find /var/www ~ -maxdepth 3 -type f \( -name "run_local.py" -o -name "app.py" \) 2>/dev/null | head -1 | xargs dirname 2>/dev/null || echo "")
    if [ -z "$PROJECT_DIR" ]; then
        echo '❌ No se encontró el directorio del proyecto'
        echo '   Busca manualmente con: find /var/www ~ -name "run_local.py"'
        exit 1
    fi
fi
cd "$PROJECT_DIR" || { echo "❌ No se pudo cambiar al directorio: $PROJECT_DIR"; exit 1; }
echo "✅ Directorio: $(pwd)"
if [ -d .git ]; then 
    echo '📥 Haciendo pull...'
    # Intentar con el usuario actual, si falla por permisos, intentar con sudo
    if git pull origin main 2>/dev/null || git pull origin master 2>/dev/null; then
        echo '✅ Git pull exitoso'
    else
        echo '⚠️  Git pull falló por permisos, intentando con sudo...'
        sudo -u deploy git pull origin main 2>/dev/null || sudo -u deploy git pull origin master 2>/dev/null || echo '⚠️  No se pudo hacer git pull (continuando...)'
    fi
fi
if [ -d venv ]; then source venv/bin/activate; fi
if [ -f requirements.txt ]; then pip install -q -r requirements.txt || true; fi
echo '🔄 Reiniciando servicio...'
# Buscar proceso gunicorn o similar
if systemctl is-active --quiet bimba.service 2>/dev/null; then
    sudo systemctl restart bimba.service && echo '✅ systemd reiniciado'
elif systemctl is-active --quiet stvaldivia.service 2>/dev/null; then
    sudo systemctl restart stvaldivia.service && echo '✅ systemd (stvaldivia) reiniciado'
elif command -v supervisorctl &>/dev/null && supervisorctl status bimba &>/dev/null 2>/dev/null; then
    sudo supervisorctl restart bimba && echo '✅ supervisor reiniciado'
elif command -v supervisorctl &>/dev/null && supervisorctl status stvaldivia &>/dev/null 2>/dev/null; then
    sudo supervisorctl restart stvaldivia && echo '✅ supervisor (stvaldivia) reiniciado'
elif command -v pm2 &>/dev/null && pm2 list | grep -q bimba; then
    pm2 restart bimba && echo '✅ PM2 reiniciado'
elif pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    # Reiniciar gunicorn si está corriendo
    GUNICORN_PID=$(pgrep -f "gunicorn.*app:create_app" | head -1)
    if [ -n "$GUNICORN_PID" ]; then
        # Intentar con el usuario actual primero
        if kill -HUP "$GUNICORN_PID" 2>/dev/null; then
            echo '✅ Gunicorn reiniciado (HUP signal)'
        else
            # Si falla, intentar con sudo
            echo '⚠️  No se pudo reiniciar con usuario actual, intentando con sudo...'
            sudo kill -HUP "$GUNICORN_PID" 2>/dev/null && echo '✅ Gunicorn reiniciado (HUP signal con sudo)' || echo '⚠️  No se pudo reiniciar gunicorn (puede requerir permisos sudo)'
        fi
    fi
elif screen -list 2>/dev/null | grep -q bimba; then
    screen -S bimba -X stuff '^C' && sleep 2 && screen -S bimba -X stuff 'python3 run_local.py\n' && echo '✅ screen reiniciado'
else
    echo '⚠️  Servicio no encontrado. Busca con: ps aux | grep python'
    echo '   Proceso actual:'
    ps aux | grep -E 'gunicorn|python.*app' | grep -v grep | head -3
fi
echo '✅ Deploy completado'
"""
                
                # Intentar primero con gcloud compute ssh
                use_gcloud = False
                try:
                    auth_check = subprocess.run(
                        ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'],
                        check=True,
                        timeout=10,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if auth_check.stdout.strip():
                        use_gcloud = True
                        # Configurar proyecto
                        subprocess.run(
                            ['gcloud', 'config', 'set', 'project', PROJECT_ID, '--quiet'],
                            check=True,
                            timeout=30,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                except:
                    use_gcloud = False
                
                current_app.logger.info(f"🚀 Iniciando deployment a VM: {INSTANCE_NAME} ({VM_IP})...")
                
                if use_gcloud:
                    # Método 1: Usar gcloud compute ssh (requiere autenticación)
                    current_app.logger.info("🔐 Usando gcloud compute ssh...")
                    try:
                        process = subprocess.Popen(
                            ['gcloud', 'compute', 'ssh', INSTANCE_NAME,
                             '--zone', ZONE,
                             '--project', PROJECT_ID,
                             '--command', deploy_script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            env=os.environ.copy()
                        )
                        stdout, stderr = process.communicate(timeout=300)
                        
                        if process.returncode == 0:
                            current_app.logger.info(f"✅ Deployment exitoso a VM")
                            if stdout:
                                current_app.logger.info(f"Output: {stdout[:500]}")
                            return
                        else:
                            error_msg = stderr[:1000] if stderr else "Error desconocido"
                            current_app.logger.warning(f"⚠️  gcloud falló: {error_msg[:200]}")
                            current_app.logger.info("🔄 Intentando con SSH directo...")
                    except Exception as e:
                        current_app.logger.warning(f"⚠️  Error con gcloud: {str(e)[:200]}")
                        current_app.logger.info("🔄 Intentando con SSH directo...")
                
                # Método 2: SSH directo (fallback, requiere SSH configurado)
                current_app.logger.info("🔐 Usando SSH directo...")
                import getpass
                import os.path
                ssh_user = getpass.getuser()
                
                # Buscar clave SSH (preferir la que generamos para GCP)
                ssh_key_paths = [
                    os.path.expanduser('~/.ssh/id_ed25519_gcp'),
                    os.path.expanduser('~/.ssh/id_rsa'),
                    os.path.expanduser('~/.ssh/id_ed25519'),
                    os.path.expanduser('~/.ssh/id_ecdsa'),
                ]
                
                ssh_key = None
                for key_path in ssh_key_paths:
                    if os.path.exists(key_path):
                        ssh_key = key_path
                        current_app.logger.info(f"🔑 Usando clave SSH: {ssh_key}")
                        break
                
                # Intentar con diferentes usuarios comunes en GCP
                # El usuario en la VM es stvaldiviazal según el prompt
                ssh_users = ['stvaldiviazal', ssh_user, 'gcp-user', 'ubuntu', 'debian']
                
                for user in ssh_users:
                    try:
                        current_app.logger.info(f"🔑 Intentando SSH como {user}@{VM_IP}...")
                        
                        # Construir comando SSH
                        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', 
                                  '-o', 'ConnectTimeout=10',
                                  '-o', 'BatchMode=yes']  # No pedir contraseña
                        
                        if ssh_key:
                            ssh_cmd.extend(['-i', ssh_key])
                        
                        ssh_cmd.append(f'{user}@{VM_IP}')
                        
                        # Ejecutar script remoto
                        process = subprocess.Popen(
                            ssh_cmd + [deploy_script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            env=os.environ.copy()
                        )
                        stdout, stderr = process.communicate(timeout=300)
                        
                        if process.returncode == 0:
                            current_app.logger.info(f"✅ Deployment exitoso a VM vía SSH")
                            if stdout:
                                current_app.logger.info(f"Output: {stdout[:500]}")
                            return
                        else:
                            if 'Permission denied' not in stderr:
                                # Si no es problema de permisos, puede ser otro error
                                current_app.logger.warning(f"⚠️  SSH falló con {user}: {stderr[:200]}")
                    except Exception as e:
                        current_app.logger.debug(f"Error intentando SSH con {user}: {str(e)[:100]}")
                        continue
                
                # Si llegamos aquí, ambos métodos fallaron
                current_app.logger.error("❌ No se pudo conectar a la VM ni con gcloud ni con SSH directo")
                current_app.logger.error("💡 Soluciones:")
                current_app.logger.error("   1. Ejecuta: gcloud auth login")
                current_app.logger.error("   2. O configura SSH keys para acceso directo")
                current_app.logger.error(f"   3. O verifica que puedes conectarte manualmente: ssh {ssh_user}@{VM_IP}")
                    
            except FileNotFoundError:
                current_app.logger.error("❌ gcloud CLI no está instalado o no está en el PATH")
            except subprocess.TimeoutExpired:
                current_app.logger.error("❌ Deployment timeout después de 10 minutos")
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr[:500] if e.stderr else str(e)
                current_app.logger.error(f"❌ Error en comando gcloud: {error_msg}")
            except Exception as e:
                current_app.logger.error(f"❌ Error al ejecutar deployment: {e}", exc_info=True)
        
        # Ejecutar en thread separado para no bloquear
        thread = Thread(target=run_deployment, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Deployment iniciado. El proceso se ejecuta en segundo plano y puede tardar varios minutos. Revisa los logs del servidor para ver el progreso.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al iniciar deployment: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al iniciar deployment: {str(e)}'
        }), 500



