"""
Rutas para la gestión de Equipo
"""
from flask import render_template, request, redirect, session, url_for, flash, jsonify
from flask import current_app
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import uuid
from app.models import db
from app.models.pos_models import Employee
from app.models.employee_shift_models import EmployeeShift, EmployeeSalaryConfig, FichaReviewLog
from app.models.employee_advance_models import EmployeeAdvance
from app.models.cargo_salary_models import CargoSalaryConfig
from app.models.cargo_models import Cargo
from app.models.delivery_models import Delivery
from app.models.survey_models import SurveyResponse
from app.models.inventory_models import InventoryItem
from app.models.jornada_models import PlanillaTrabajador, Jornada
from app.helpers.timezone_utils import format_date_spanish
from app.helpers.timezone_utils import CHILE_TZ
from sqlalchemy import func, and_, or_

# El blueprint se importa desde __init__.py
from . import equipo_bp

def require_admin():
    """Verifica que el usuario esté autenticado como administrador"""
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    return None

@equipo_bp.route('/')
def index():
    """Página principal de gestión de equipo"""
    require_admin()
    return redirect(url_for('equipo.listar'))

@equipo_bp.route('/listar')
def listar():
    """Listar todos los miembros del equipo (solo locales)"""
    if require_admin():
        return require_admin()
    
    try:
        # Inicializar cargos por defecto si no existen
        _initialize_default_cargos()
        
        # Solo empleados locales (no sincronizados desde PHP POS)
        # Por defecto mostrar solo activos, pero si no hay activos, mostrar todos para debugging
        employees = Employee.query.order_by(Employee.name).all()
        
        # Filtrar solo activos si hay empleados activos
        active_employees = [e for e in employees if e.is_active]
        if active_employees:
            employees = active_employees
        # Si no hay activos pero sí hay empleados, mostrar todos para debugging
        
        # Verificar si el usuario es superadmin
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
        
        current_app.logger.info(f"Equipo listar: {len(employees)} empleados encontrados (de {Employee.query.count()} total)")
        return render_template('admin/equipo/listar.html', 
                             employees=employees,
                             is_superadmin=is_superadmin,
                             current_username=session.get('admin_username', ''))
    except Exception as e:
        current_app.logger.error(f"Error al listar equipo: {e}", exc_info=True)
        flash(f"Error al cargar equipo: {str(e)}", "error")
        return redirect(url_for('routes.admin_panel_control'))

def _initialize_default_cargos():
    """Inicializa los cargos por defecto si no existen"""
    try:
        cargos_default = [
            ('BARRA', 1, 'Personal de barra y servicio de bebidas'),
            ('COPERX', 2, 'Coperx - Personal de servicio'),
            ('CAJA', 3, 'Personal de caja y cobro'),
            ('GUARDIA', 4, 'Personal de seguridad y guardia'),
            ('ANFITRIONA', 5, 'Anfitriona - Recepción y atención al cliente'),
            ('ASEO', 6, 'Personal de limpieza y aseo'),
            ('GUARDARROP', 7, 'Personal de guardarropa'),
            ('TÉCNICA', 8, 'Personal técnico y mantenimiento'),
            ('DRAG', 9, 'Artistas drag'),
            ('DJ', 10, 'DJs y música'),
            ('Supervisor', 11, 'Supervisores'),
            ('Administrador', 12, 'Personal administrativo'),
            ('Otro', 13, 'Otros cargos')
        ]
        
        cargos_creados = 0
        for nombre, orden, descripcion in cargos_default:
            cargo_existente = Cargo.query.filter_by(nombre=nombre).first()
            if not cargo_existente:
                nuevo_cargo = Cargo(
                    nombre=nombre,
                    descripcion=descripcion,
                    activo=True,
                    orden=orden
                )
                db.session.add(nuevo_cargo)
                cargos_creados += 1
                
                # Crear configuración de sueldo por defecto si no existe
                cargo_salary_existente = CargoSalaryConfig.query.filter_by(cargo=nombre).first()
                if not cargo_salary_existente:
                    cargo_salary = CargoSalaryConfig(
                        cargo=nombre,
                        sueldo_por_turno=0.0,
                        bono_fijo=0.0
                    )
                    db.session.add(cargo_salary)
        
        if cargos_creados > 0:
            db.session.commit()
            current_app.logger.info(f"✅ {cargos_creados} cargos por defecto inicializados")
        else:
            # No hay cambios, pero verificar que todos tengan su configuración de sueldo
            for nombre, _, _ in cargos_default:
                cargo_salary_existente = CargoSalaryConfig.query.filter_by(cargo=nombre).first()
                if not cargo_salary_existente:
                    cargo_salary = CargoSalaryConfig(
                        cargo=nombre,
                        sueldo_por_turno=0.0,
                        bono_fijo=0.0
                    )
                    db.session.add(cargo_salary)
                    cargos_creados += 1
            
            if cargos_creados > 0:
                db.session.commit()
                current_app.logger.info(f"✅ {cargos_creados} configuraciones de sueldo creadas para cargos existentes")
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"⚠️  Error al inicializar cargos por defecto: {e}")

@equipo_bp.route('/ficha/<employee_id>')
def ficha_personal(employee_id):
    """Ficha personal del miembro del equipo con historial de turnos y cálculo de sueldo"""
    if require_admin():
        return require_admin()
    
    try:
        # Registrar revisión de ficha
        try:
            reviewer_name = session.get('admin_username', 'Admin')
            # Obtener hora actual en Chile y convertir a UTC para almacenar
            now_chile = datetime.now(CHILE_TZ)
            now_utc = now_chile.astimezone(pytz.UTC).replace(tzinfo=None)
            
            review_log = FichaReviewLog(
                employee_id=employee_id,
                employee_name='',  # Se actualizará después
                reviewer_name=reviewer_name,
                reviewer_session_id=session.get('session_id', ''),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500],  # Limitar longitud
                reviewed_at=now_utc  # Establecer explícitamente la hora en UTC
            )
            db.session.add(review_log)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error al registrar revisión de ficha: {e}", exc_info=True)
            # No fallar si no se puede registrar el log
        
        # Obtener empleado (solo locales)
        employee = Employee.query.filter(
            Employee.id == employee_id,
            
        ).first()
        if not employee:
            flash("Miembro del equipo no encontrado.", "error")
            return redirect(url_for('equipo.listar'))
        
        # Actualizar nombre del empleado en el log si se creó antes de obtener el empleado
        try:
            review_log.employee_name = employee.name or 'Sin nombre'
            db.session.commit()
        except:
            pass
        
        # Obtener configuración de sueldo
        salary_config = EmployeeSalaryConfig.query.filter_by(employee_id=employee_id).first()
        sueldo_por_turno = float(salary_config.sueldo_por_turno) if salary_config else 0.0
        
        # Obtener turnos del empleado (todos, no limitar)
        # Convertir employee_id a string para asegurar compatibilidad
        employee_id_str = str(employee_id)
        shifts = EmployeeShift.query.filter_by(employee_id=employee_id_str).order_by(
            EmployeeShift.fecha_turno.desc(), 
            EmployeeShift.hora_inicio.desc()
        ).all()
        
        # Log para debugging
        current_app.logger.info(
            f"📋 Consultando turnos para employee_id={employee_id_str} (tipo: {type(employee_id_str).__name__}), "
            f"encontrados: {len(shifts)} turnos"
        )
        
        # Calcular estadísticas básicas
        total_turnos = len(shifts)
        turnos_pagados = len([s for s in shifts if s.pagado])
        turnos_pendientes = total_turnos - turnos_pagados
        
        # Calcular días trabajados (días únicos)
        dias_trabajados = len(set([s.fecha_turno for s in shifts]))
        
        # Calcular sueldos
        sueldo_total = sum([float(s.sueldo_turno or 0) for s in shifts])
        sueldo_pagado = sum([float(s.sueldo_turno or 0) for s in shifts if s.pagado])
        
        # Obtener abonos/pagos excepcionales (no aplicados aún)
        abonos = EmployeeAdvance.query.filter_by(
            employee_id=employee_id,
            aplicado=False
        ).all()
        total_abonos = sum([float(a.monto or 0) for a in abonos])
        
        # El sueldo pendiente se calcula restando los abonos
        sueldo_pendiente = (sueldo_total - sueldo_pagado) - total_abonos
        
        # Calcular estadísticas avanzadas
        costo_por_dia = sueldo_total / dias_trabajados if dias_trabajados > 0 else 0.0
        promedio_sueldo_turno = sueldo_total / total_turnos if total_turnos > 0 else 0.0
        promedio_turnos_por_dia = total_turnos / dias_trabajados if dias_trabajados > 0 else 0.0
        
        # Calcular bonos y descuentos totales
        bonos_totales = sum([float(s.bonos or 0) for s in shifts])
        descuentos_totales = sum([float(s.descuentos or 0) for s in shifts])
        
        # Calcular estadísticas por mes (últimos 6 meses)
        estadisticas_por_mes = defaultdict(lambda: {
            'turnos': 0,
            'sueldo': 0.0,
            'dias': set()
        })
        
        fecha_limite = datetime.now(CHILE_TZ) - timedelta(days=180)  # 6 meses
        
        for shift in shifts:
            try:
                fecha_turno = datetime.strptime(shift.fecha_turno, '%Y-%m-%d')
                fecha_turno = CHILE_TZ.localize(fecha_turno)
                
                if fecha_turno >= fecha_limite:
                    mes_key = fecha_turno.strftime('%Y-%m')
                    estadisticas_por_mes[mes_key]['turnos'] += 1
                    estadisticas_por_mes[mes_key]['sueldo'] += float(shift.sueldo_turno or 0)
                    estadisticas_por_mes[mes_key]['dias'].add(shift.fecha_turno)
            except:
                pass
        
        # Formatear estadísticas por mes
        estadisticas_mensuales = []
        for mes, datos in sorted(estadisticas_por_mes.items(), reverse=True):
            estadisticas_mensuales.append({
                'mes': mes,
                'turnos': datos['turnos'],
                'sueldo': datos['sueldo'],
                'dias': len(datos['dias'])
            })
        
        # Calcular estadísticas de rendimiento
        # Período actual (último mes)
        fecha_actual = datetime.now(CHILE_TZ)
        fecha_inicio_mes_actual = fecha_actual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fecha_inicio_mes_anterior = (fecha_inicio_mes_actual - timedelta(days=1)).replace(day=1)
        
        # Turnos del mes actual
        turnos_mes_actual = [s for s in shifts if s.fecha_turno >= fecha_inicio_mes_actual.strftime('%Y-%m-%d')]
        turnos_mes_anterior = [s for s in shifts if 
                               fecha_inicio_mes_anterior.strftime('%Y-%m-%d') <= s.fecha_turno < fecha_inicio_mes_actual.strftime('%Y-%m-%d')]
        
        # Estadísticas del mes actual
        turnos_actual = len(turnos_mes_actual)
        sueldo_actual = sum([float(s.sueldo_turno or 0) for s in turnos_mes_actual])
        dias_actual = len(set([s.fecha_turno for s in turnos_mes_actual]))
        
        # Estadísticas del mes anterior
        turnos_anterior = len(turnos_mes_anterior)
        sueldo_anterior = sum([float(s.sueldo_turno or 0) for s in turnos_mes_anterior])
        dias_anterior = len(set([s.fecha_turno for s in turnos_mes_anterior]))
        
        # Calcular variaciones
        variacion_turnos = ((turnos_actual - turnos_anterior) / turnos_anterior * 100) if turnos_anterior > 0 else 0.0
        variacion_sueldo = ((sueldo_actual - sueldo_anterior) / sueldo_anterior * 100) if sueldo_anterior > 0 else 0.0
        variacion_dias = ((dias_actual - dias_anterior) / dias_anterior * 100) if dias_anterior > 0 else 0.0
        
        # Tasa de cumplimiento (turnos pagados vs total)
        tasa_cumplimiento = (turnos_pagados / total_turnos * 100) if total_turnos > 0 else 0.0
        
        # Promedio de horas trabajadas
        horas_totales = sum([float(s.horas_trabajadas or 0) for s in shifts if s.horas_trabajadas])
        promedio_horas = horas_totales / total_turnos if total_turnos > 0 else 0.0
        
        # Mejor mes (más turnos)
        mejor_mes = None
        if estadisticas_mensuales:
            mejor_mes = max(estadisticas_mensuales, key=lambda x: x['turnos'])
        
        # Consistencia (desviación estándar de turnos por mes)
        import statistics
        turnos_por_mes = [m['turnos'] for m in estadisticas_mensuales]
        if len(turnos_por_mes) > 1:
            try:
                desviacion_turnos = statistics.stdev(turnos_por_mes)
                promedio_turnos_mes = statistics.mean(turnos_por_mes)
                coeficiente_variacion = (desviacion_turnos / promedio_turnos_mes * 100) if promedio_turnos_mes > 0 else 0.0
            except:
                desviacion_turnos = 0.0
                coeficiente_variacion = 0.0
        else:
            desviacion_turnos = 0.0
            coeficiente_variacion = 0.0
        
        # Calcular días desde último turno
        ultimo_turno = shifts[0] if shifts else None
        dias_desde_ultimo_turno = None
        if ultimo_turno:
            try:
                fecha_ultimo = datetime.strptime(ultimo_turno.fecha_turno, '%Y-%m-%d')
                fecha_ultimo = CHILE_TZ.localize(fecha_ultimo)
                dias_desde_ultimo_turno = (datetime.now(CHILE_TZ) - fecha_ultimo).days
            except:
                dias_desde_ultimo_turno = None
        
        # Calcular frecuencia de trabajo (turnos por semana promedio)
        semanas_trabajadas = dias_trabajados / 7.0 if dias_trabajados > 0 else 0.0
        frecuencia_semanal = total_turnos / semanas_trabajadas if semanas_trabajadas > 0 else 0.0
        
        # ===== ESTADÍSTICAS BASADAS EN TICKETS Y ENCUESTAS =====
        # Obtener entregas (tragos) del empleado por nombre
        employee_name = employee.name
        # Búsqueda case-insensitive (compatible MySQL)
        deliveries = Delivery.query.filter(
            func.lower(Delivery.bartender).like(func.lower(f'%{employee_name}%'))
        ).all()
        
        # Calcular estadísticas de entregas
        total_tragos_entregados = sum([d.qty for d in deliveries])
        total_entregas = len(deliveries)
        
        # Agrupar entregas por fecha (noche)
        entregas_por_fecha = defaultdict(lambda: {'tragos': 0, 'entregas': 0})
        for delivery in deliveries:
            fecha_key = delivery.timestamp.strftime('%Y-%m-%d') if delivery.timestamp else None
            if fecha_key:
                entregas_por_fecha[fecha_key]['tragos'] += delivery.qty
                entregas_por_fecha[fecha_key]['entregas'] += 1
        
        # Calcular promedio de tragos por noche
        noches_trabajadas = len(entregas_por_fecha)
        promedio_tragos_por_noche = total_tragos_entregados / noches_trabajadas if noches_trabajadas > 0 else 0.0
        
        # Calcular ritmo de trabajo (tragos por hora) por noche
        ritmo_por_noche = []
        for fecha_key, datos in entregas_por_fecha.items():
            # Obtener entregas de esa fecha
            fecha_deliveries = [d for d in deliveries if d.timestamp and d.timestamp.strftime('%Y-%m-%d') == fecha_key]
            if fecha_deliveries:
                # Calcular horas trabajadas (diferencia entre primera y última entrega)
                timestamps = sorted([d.timestamp for d in fecha_deliveries if d.timestamp])
                if len(timestamps) > 1:
                    horas_trabajadas = (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0
                    if horas_trabajadas > 0:
                        ritmo = datos['tragos'] / horas_trabajadas
                        ritmo_por_noche.append({
                            'fecha': fecha_key,
                            'tragos': datos['tragos'],
                            'horas': horas_trabajadas,
                            'ritmo': ritmo
                        })
        
        # Promedio de ritmo de trabajo
        promedio_ritmo = sum([r['ritmo'] for r in ritmo_por_noche]) / len(ritmo_por_noche) if ritmo_por_noche else 0.0
        
        # Mejor noche (más tragos entregados)
        mejor_noche = None
        if entregas_por_fecha:
            mejor_fecha = max(entregas_por_fecha.items(), key=lambda x: x[1]['tragos'])
            mejor_noche = {
                'fecha': mejor_fecha[0],
                'tragos': mejor_fecha[1]['tragos'],
                'entregas': mejor_fecha[1]['entregas']
            }
        
        # Obtener encuestas relacionadas con el empleado
        # Buscar por nombre de bartender en encuestas (compatible MySQL)
        survey_responses = SurveyResponse.query.filter(
            func.lower(SurveyResponse.bartender_nombre).like(func.lower(f'%{employee_name}%'))
        ).all()
        
        # También buscar por barra si el empleado trabajó en alguna barra
        # Obtener barras únicas donde trabajó el empleado
        barras_trabajadas = set([d.barra for d in deliveries if d.barra])
        if barras_trabajadas:
            # Buscar encuestas de esas barras en las fechas que trabajó
            fechas_trabajadas = set([d.timestamp.strftime('%Y-%m-%d') if d.timestamp else None for d in deliveries])
            fechas_trabajadas = [f for f in fechas_trabajadas if f]
            
            if fechas_trabajadas:
                from datetime import datetime as dt
                survey_by_barra = SurveyResponse.query.filter(
                    SurveyResponse.barra.in_(barras_trabajadas),
                    SurveyResponse.fecha_sesion.in_([dt.strptime(f, '%Y-%m-%d').date() for f in fechas_trabajadas])
                ).all()
                survey_responses.extend(survey_by_barra)
        
        # Eliminar duplicados
        survey_responses = list({r.id: r for r in survey_responses}.values())
        
        # Calcular estadísticas de encuestas
        total_encuestas = len(survey_responses)
        if total_encuestas > 0:
            promedio_rating = sum([r.rating for r in survey_responses]) / total_encuestas
            ratings_distribucion = defaultdict(int)
            for r in survey_responses:
                ratings_distribucion[r.rating] += 1
        else:
            promedio_rating = 0.0
            ratings_distribucion = {}
        
        # Calcular estadísticas de entregas por mes
        entregas_por_mes = defaultdict(lambda: {'tragos': 0, 'entregas': 0, 'noches': set()})
        for delivery in deliveries:
            if delivery.timestamp:
                fecha_key = delivery.timestamp.strftime('%Y-%m')
                fecha_dia = delivery.timestamp.strftime('%Y-%m-%d')
                entregas_por_mes[fecha_key]['tragos'] += delivery.qty
                entregas_por_mes[fecha_key]['entregas'] += 1
                entregas_por_mes[fecha_key]['noches'].add(fecha_dia)
        
        # Formatear entregas por mes
        estadisticas_entregas_mensuales = []
        for mes, datos in sorted(entregas_por_mes.items(), reverse=True)[:6]:  # Últimos 6 meses
            estadisticas_entregas_mensuales.append({
                'mes': mes,
                'tragos': datos['tragos'],
                'entregas': datos['entregas'],
                'noches': len(datos['noches'])
            })
        
        # ===== ESTADÍSTICAS DE PUNTUALIDAD (Apertura/Cierre de Barra) =====
        # Inicializar estadísticas de puntualidad con valores por defecto
        puntualidad_stats = {
            'total_jornadas': 0,
            'jornadas_puntuales': 0,
            'jornadas_tardes': 0,
            'promedio_retraso_apertura': 0.0,
            'promedio_retraso_cierre': 0.0,
            'tasa_puntualidad': 0.0
        }
        
        try:
            # Obtener jornadas donde trabajó el empleado
            jornadas_empleado = db.session.query(Jornada).join(
                PlanillaTrabajador,
                PlanillaTrabajador.jornada_id == Jornada.id
            ).filter(
                PlanillaTrabajador.id_empleado == employee_id
            ).order_by(Jornada.fecha_jornada.desc()).all()
            
            puntualidad_stats['total_jornadas'] = len(jornadas_empleado)
            
            retrasos_apertura = []
            retrasos_cierre = []
            
            for jornada in jornadas_empleado:
                # Obtener planilla del empleado en esta jornada
                planilla = PlanillaTrabajador.query.filter_by(
                    jornada_id=jornada.id,
                    id_empleado=employee_id
                ).first()
                
                if not planilla:
                    continue
                
                # Obtener entregas del empleado en la fecha de la jornada
                fecha_jornada = jornada.fecha_jornada
                entregas_jornada = [d for d in deliveries if 
                                   d.timestamp and d.timestamp.strftime('%Y-%m-%d') == fecha_jornada]
                
                if not entregas_jornada:
                    continue
                
                # Calcular hora real de inicio (primera entrega)
                primera_entrega = min(entregas_jornada, key=lambda x: x.timestamp if x.timestamp else datetime.max)
                ultima_entrega = max(entregas_jornada, key=lambda x: x.timestamp if x.timestamp else datetime.min)
                
                if primera_entrega.timestamp and planilla.hora_inicio:
                    try:
                        # Parsear hora programada
                        hora_programada_str = planilla.hora_inicio
                        hora_programada = datetime.strptime(hora_programada_str, '%H:%M').time()
                        
                        # Obtener hora real (primera entrega)
                        hora_real = primera_entrega.timestamp.time()
                        
                        # Calcular diferencia en minutos
                        hora_programada_dt = datetime.combine(primera_entrega.timestamp.date(), hora_programada)
                        hora_real_dt = datetime.combine(primera_entrega.timestamp.date(), hora_real)
                        
                        # Si la hora real es muy temprano (antes de medianoche), podría ser del día siguiente
                        if hora_real < hora_programada and hora_real.hour < 12:
                            hora_real_dt = datetime.combine(
                                primera_entrega.timestamp.date() + timedelta(days=1), 
                                hora_real
                            )
                        
                        diferencia_minutos = (hora_real_dt - hora_programada_dt).total_seconds() / 60.0
                        
                        if diferencia_minutos > 0:  # Tarde
                            retrasos_apertura.append(diferencia_minutos)
                            puntualidad_stats['jornadas_tardes'] += 1
                        else:  # Puntual o temprano
                            puntualidad_stats['jornadas_puntuales'] += 1
                        
                        # Calcular retraso en cierre (última entrega vs hora programada de fin)
                        if planilla.hora_fin and ultima_entrega.timestamp:
                            hora_fin_programada_str = planilla.hora_fin
                            hora_fin_programada = datetime.strptime(hora_fin_programada_str, '%H:%M').time()
                            hora_fin_real = ultima_entrega.timestamp.time()
                            
                            hora_fin_programada_dt = datetime.combine(ultima_entrega.timestamp.date(), hora_fin_programada)
                            hora_fin_real_dt = datetime.combine(ultima_entrega.timestamp.date(), hora_fin_real)
                            
                            # Ajustar si cruza medianoche
                            if hora_fin_programada.hour > 12 and hora_fin_real.hour < 12:
                                hora_fin_real_dt = datetime.combine(
                                    ultima_entrega.timestamp.date() + timedelta(days=1),
                                    hora_fin_real
                                )
                            
                            diferencia_cierre = (hora_fin_real_dt - hora_fin_programada_dt).total_seconds() / 60.0
                            if diferencia_cierre > 0:
                                retrasos_cierre.append(diferencia_cierre)
                    
                    except Exception as e:
                        current_app.logger.warning(f"Error al calcular puntualidad: {e}")
                        continue
            
            # Calcular promedios
            if retrasos_apertura:
                puntualidad_stats['promedio_retraso_apertura'] = sum(retrasos_apertura) / len(retrasos_apertura)
            if retrasos_cierre:
                puntualidad_stats['promedio_retraso_cierre'] = sum(retrasos_cierre) / len(retrasos_cierre)
            
            if puntualidad_stats['total_jornadas'] > 0:
                puntualidad_stats['tasa_puntualidad'] = (
                    puntualidad_stats['jornadas_puntuales'] / puntualidad_stats['total_jornadas'] * 100
                )
        except Exception as e:
            current_app.logger.warning(f"Error al calcular estadísticas de puntualidad: {e}", exc_info=True)
        
        # ===== ESTADÍSTICAS DE EFICIENCIA (Merma del Inventario) =====
        # Inicializar estadísticas de eficiencia con valores por defecto
        eficiencia_stats = {
            'total_inventarios': 0,
            'inventarios_sin_merma': 0,
            'inventarios_con_merma': 0,
            'merma_total': 0.0,
            'merma_promedio': 0.0,
            'eficiencia_promedio': 0.0,
            'mejor_inventario': None,
            'peor_inventario': None
        }
        
        try:
            # Obtener barras donde trabajó el empleado
            barras_empleado = set([d.barra for d in deliveries if d.barra])
            
            inventarios_evaluados = []
            
            for barra in barras_empleado:
                # Obtener fechas donde trabajó en esta barra
                fechas_barra = set([
                    d.timestamp.strftime('%Y-%m-%d') 
                    for d in deliveries 
                    if d.barra == barra and d.timestamp
                ])
                
                for fecha_str in fechas_barra:
                    try:
                        fecha_date = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                        
                        # Obtener items de inventario de esta barra y fecha
                        items_inventario = InventoryItem.query.filter_by(
                            shift_date=fecha_date,
                            barra=barra,
                            status='closed'  # Solo inventarios cerrados
                        ).all()
                        
                        if not items_inventario:
                            continue
                        
                        # Calcular merma total del inventario
                        merma_total_inventario = 0.0
                        items_con_merma = 0
                        items_sin_merma = 0
                        
                        for item in items_inventario:
                            if item.final_quantity is not None:
                                # Calcular cantidad esperada
                                cantidad_esperada = item.initial_quantity - item.delivered_quantity
                                # Calcular diferencia (merma si es negativa)
                                diferencia = item.final_quantity - cantidad_esperada
                                
                                if diferencia < 0:  # Hay merma
                                    merma_total_inventario += abs(diferencia)
                                    items_con_merma += 1
                                else:
                                    items_sin_merma += 1
                        
                        if items_inventario:
                            eficiencia = (items_sin_merma / len(items_inventario)) * 100 if items_inventario else 0.0
                            
                            inventario_data = {
                                'fecha': fecha_str,
                                'barra': barra,
                                'merma': merma_total_inventario,
                                'items_total': len(items_inventario),
                                'items_con_merma': items_con_merma,
                                'items_sin_merma': items_sin_merma,
                                'eficiencia': eficiencia
                            }
                            
                            inventarios_evaluados.append(inventario_data)
                            
                            eficiencia_stats['total_inventarios'] += 1
                            eficiencia_stats['merma_total'] += merma_total_inventario
                            
                            if items_con_merma == 0:
                                eficiencia_stats['inventarios_sin_merma'] += 1
                            else:
                                eficiencia_stats['inventarios_con_merma'] += 1
                    
                    except Exception as e:
                        current_app.logger.warning(f"Error al calcular eficiencia para {barra} en {fecha_str}: {e}")
                        continue
            
            # Calcular promedios de eficiencia
            if inventarios_evaluados:
                eficiencia_stats['merma_promedio'] = eficiencia_stats['merma_total'] / len(inventarios_evaluados)
                eficiencia_stats['eficiencia_promedio'] = sum([inv['eficiencia'] for inv in inventarios_evaluados]) / len(inventarios_evaluados)
                
                # Mejor y peor inventario
                mejor_inv = min(inventarios_evaluados, key=lambda x: x['merma'])
                peor_inv = max(inventarios_evaluados, key=lambda x: x['merma'])
                
                eficiencia_stats['mejor_inventario'] = mejor_inv
                eficiencia_stats['peor_inventario'] = peor_inv
        except Exception as e:
            current_app.logger.warning(f"Error al calcular estadísticas de eficiencia: {e}", exc_info=True)
        
        # Estadísticas de rendimiento
        rendimiento_stats = {
            'turnos_mes_actual': turnos_actual,
            'turnos_mes_anterior': turnos_anterior,
            'variacion_turnos': variacion_turnos,
            'sueldo_mes_actual': sueldo_actual,
            'sueldo_mes_anterior': sueldo_anterior,
            'variacion_sueldo': variacion_sueldo,
            'dias_mes_actual': dias_actual,
            'dias_mes_anterior': dias_anterior,
            'variacion_dias': variacion_dias,
            'tasa_cumplimiento': tasa_cumplimiento,
            'promedio_horas': promedio_horas,
            'mejor_mes': mejor_mes,
            'coeficiente_variacion': coeficiente_variacion,
            'dias_desde_ultimo_turno': dias_desde_ultimo_turno,
            'frecuencia_semanal': frecuencia_semanal,
            'semanas_trabajadas': semanas_trabajadas,
            # Estadísticas de tickets/entregas
            'total_tragos_entregados': total_tragos_entregados,
            'total_entregas': total_entregas,
            'noches_trabajadas': noches_trabajadas,
            'promedio_tragos_por_noche': promedio_tragos_por_noche,
            'promedio_ritmo_trabajo': promedio_ritmo,
            'mejor_noche': mejor_noche,
            'estadisticas_entregas_mensuales': estadisticas_entregas_mensuales,
            # Estadísticas de encuestas
            'total_encuestas': total_encuestas,
            'promedio_rating': promedio_rating,
            'ratings_distribucion': dict(ratings_distribucion),
            # Estadísticas de puntualidad
            'puntualidad': puntualidad_stats,
            # Estadísticas de eficiencia
            'eficiencia': eficiencia_stats
        }
        
        # Formatear turnos
        # Log para debugging
        current_app.logger.info(
            f"📊 Procesando {len(shifts)} turnos para crear shifts_data"
        )
        
        shifts_data = []
        for shift in shifts:
            hora_inicio_chile = shift.hora_inicio
            if hora_inicio_chile.tzinfo is None:
                hora_inicio_chile = pytz.UTC.localize(hora_inicio_chile)
            hora_inicio_chile = hora_inicio_chile.astimezone(CHILE_TZ)
            
            hora_fin_chile = None
            if shift.hora_fin:
                hora_fin_chile = shift.hora_fin
                if hora_fin_chile.tzinfo is None:
                    hora_fin_chile = pytz.UTC.localize(hora_fin_chile)
                hora_fin_chile = hora_fin_chile.astimezone(CHILE_TZ)
            
            shifts_data.append({
                'id': shift.id,
                'fecha_turno': format_date_spanish(date_str=shift.fecha_turno),
                'tipo_turno': shift.tipo_turno or 'N/A',
                'cargo': shift.cargo or 'N/A',
                'hora_inicio': hora_inicio_chile.strftime('%H:%M'),
                'hora_fin': hora_fin_chile.strftime('%H:%M') if hora_fin_chile else 'En curso',
                'horas_trabajadas': float(shift.horas_trabajadas) if shift.horas_trabajadas else None,
                'sueldo_por_turno': float(shift.sueldo_por_turno) if shift.sueldo_por_turno else 0.0,
                'sueldo_turno': float(shift.sueldo_turno) if shift.sueldo_turno else 0.0,
                'bonos': float(shift.bonos),
                'descuentos': float(shift.descuentos),
                'estado': shift.estado,
                'pagado': shift.pagado,
                'fecha_pago': shift.fecha_pago.isoformat() if shift.fecha_pago else None,
                'notas': shift.notas
            })
        
        # Log final para debugging
        current_app.logger.info(
            f"✅ shifts_data creado con {len(shifts_data)} turnos para employee_id={employee_id_str}"
        )
        
        # Obtener log de revisiones (últimas 20)
        review_logs = FichaReviewLog.query.filter_by(employee_id=employee_id)\
            .order_by(FichaReviewLog.reviewed_at.desc())\
            .limit(20).all()
        
        review_logs_data = []
        for log in review_logs:
            # Convertir UTC almacenado de vuelta a hora de Chile para mostrar
            reviewed_at_chile_str = 'N/A'
            if log.reviewed_at:
                # Si no tiene tzinfo, asumir que es UTC
                if log.reviewed_at.tzinfo is None:
                    reviewed_at_utc = pytz.UTC.localize(log.reviewed_at)
                else:
                    reviewed_at_utc = log.reviewed_at
                reviewed_at_chile = reviewed_at_utc.astimezone(CHILE_TZ)
                # Convertir a string formateado para evitar problemas con timezone-aware datetime en template
                reviewed_at_chile_str = reviewed_at_chile.strftime('%d/%m/%Y %H:%M:%S')
            
            review_logs_data.append({
                'reviewer_name': log.reviewer_name or 'Desconocido',
                'reviewed_at': reviewed_at_chile_str,  # Hora en Chile formateada como string
                'ip_address': log.ip_address or 'N/A'
            })
        
        # Obtener abonos/pagos excepcionales del empleado
        abonos = EmployeeAdvance.query.filter_by(employee_id=employee_id).order_by(
            EmployeeAdvance.fecha_abono.desc(),
            EmployeeAdvance.created_at.desc()
        ).all()
        
        abonos_data = []
        total_abonos_pendientes = 0.0
        total_abonos_aplicados = 0.0
        
        for abono in abonos:
            abono_dict = abono.to_dict()
            abonos_data.append(abono_dict)
            if not abono.aplicado:
                total_abonos_pendientes += float(abono.monto or 0)
            else:
                total_abonos_aplicados += float(abono.monto or 0)
        
        # Recalcular sueldo pendiente considerando abonos
        sueldo_pendiente_con_abonos = sueldo_pendiente - total_abonos_pendientes
        
        return render_template('admin/equipo/ficha.html',
                             employee=employee,
                             salary_config=salary_config,
                             shifts=shifts_data,
                             total_turnos=total_turnos,
                             turnos_pagados=turnos_pagados,
                             turnos_pendientes=turnos_pendientes,
                             sueldo_total=sueldo_total,
                             sueldo_pagado=sueldo_pagado,
                             sueldo_pendiente=sueldo_pendiente,
                             sueldo_pendiente_con_abonos=sueldo_pendiente_con_abonos,
                             sueldo_por_turno=sueldo_por_turno,
                             dias_trabajados=dias_trabajados,
                             costo_por_dia=costo_por_dia,
                             promedio_sueldo_turno=promedio_sueldo_turno,
                             promedio_turnos_por_dia=promedio_turnos_por_dia,
                             bonos_totales=bonos_totales,
                             descuentos_totales=descuentos_totales,
                             estadisticas_mensuales=estadisticas_mensuales,
                             rendimiento=rendimiento_stats,
                             review_logs=review_logs_data,
                             abonos=abonos_data,
                             total_abonos_pendientes=total_abonos_pendientes,
                             total_abonos_aplicados=total_abonos_aplicados)
    except Exception as e:
        current_app.logger.error(f"Error al cargar ficha personal: {e}", exc_info=True)
        flash(f"Error al cargar ficha personal: {str(e)}", "error")
        return redirect(url_for('equipo.listar'))

@equipo_bp.route('/api/employees', methods=['GET', 'POST'])
def api_employees():
    """API: Listar o crear miembros del equipo"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    if request.method == 'GET':
        # Listar empleados (solo locales, no sincronizados desde PHP POS)
        try:
            from app.helpers.pagination import paginate_query
            
            # Query base con paginación
            query = Employee.query.filter(Employee.is_active == True).order_by(Employee.name)
            
            # Paginar si se solicita, sino retornar todos (para compatibilidad)
            if request.args.get('paginate', 'false').lower() == 'true':
                employees, metadata = paginate_query(query, per_page=50)
                
                employees_data = []
                for emp in employees:
                    employees_data.append({
                        'id': str(emp.id),
                        'name': emp.name or '',
                        'cargo': emp.cargo or '',
                        'pin': emp.pin or '',
                        'active': emp.is_active if hasattr(emp, 'is_active') else True
                    })
                
                return jsonify({
                    'success': True,
                    'employees': employees_data,
                    'equipo': employees_data,  # Alias para compatibilidad
                    'pagination': metadata
                })
            else:
                # Sin paginación (compatibilidad hacia atrás)
                employees = query.all()
                employees_data = []
                for emp in employees:
                    employees_data.append({
                        'id': str(emp.id),
                        'name': emp.name or '',
                        'cargo': emp.cargo or '',
                        'pin': emp.pin or '',
                        'active': emp.is_active if hasattr(emp, 'is_active') else True
                    })
                
                return jsonify({
                    'success': True,
                    'employees': employees_data,
                    'equipo': employees_data  # Alias para compatibilidad
                })
        except Exception as e:
            current_app.logger.error(f"Error al listar empleados: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        # Crear empleado
        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            cargo = data.get('cargo', '').strip()
            pin = data.get('pin', '').strip()
            active = data.get('active', True)
            
            if not name:
                return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400
            
            # Verificar si ya existe un empleado local con el mismo nombre
            existing = Employee.query.filter(
                Employee.name == name,
                
            ).first()
            if existing:
                return jsonify({'success': False, 'message': 'Ya existe otro miembro del equipo con ese nombre'}), 400
            
            # Generar ID simple y secuencial (números simples: 1, 2, 3, ...)
            # Buscar el máximo ID numérico existente entre empleados locales
            local_employees = Employee.query.filter(
                
            ).all()
            
            # Encontrar el máximo ID numérico
            max_id = 0
            for emp in local_employees:
                try:
                    # Intentar convertir el ID a número
                    if emp.id.isdigit():
                        emp_id_num = int(emp.id)
                        if emp_id_num > max_id:
                            max_id = emp_id_num
                except:
                    # Si no es numérico (UUID antiguo), ignorar
                    pass
            
            # El nuevo ID será el siguiente número disponible
            employee_id = str(max_id + 1)
            
            # Verificar que el ID no exista (por seguridad)
            existing_id = Employee.query.filter_by(id=employee_id).first()
            if existing_id:
                # Si existe, buscar el siguiente disponible
                while existing_id:
                    max_id += 1
                    employee_id = str(max_id)
                    existing_id = Employee.query.filter_by(id=employee_id).first()
            
            # Determinar si es bartender o cajero según el cargo (cargos principales)
            cargo_lower = cargo.lower() if cargo else ''
            is_bartender = 'barra' in cargo_lower or cargo_lower == 'bartender' or cargo_lower == 'coperx'
            is_cashier = cargo_lower == 'caja' or cargo_lower == 'cajero'
            
            # Crear empleado (solo local, no sincronizado desde PHP POS)
            # El ID es único e inmutable - nunca se puede cambiar
            new_employee = Employee(
                id=employee_id,  # ID único e inmutable - identifica al trabajador permanentemente
                name=name,
                cargo=cargo,
                pin=pin if pin else None,
                is_active=active,
                is_bartender=is_bartender,
                is_cashier=is_cashier,
                synced_from_phppos=False,  # Empleado local
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_employee)
            db.session.commit()
            
            current_app.logger.info(f"Miembro del equipo creado: {name} (ID: {employee_id})")
            return jsonify({'success': True, 'message': 'Miembro del equipo creado correctamente'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear empleado: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/employees/<employee_id>', methods=['GET', 'PUT', 'DELETE'])
def api_employee_detail(employee_id):
    """API: Obtener, actualizar o eliminar un miembro del equipo"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Solo buscar empleados locales
    employee = Employee.query.filter(
        Employee.id == employee_id,
        
    ).first()
    if not employee:
        return jsonify({'success': False, 'message': 'Miembro del equipo no encontrado'}), 404
    
    if request.method == 'GET':
        # Obtener empleado
        return jsonify({
            'success': True,
            'employee': {
                'id': str(employee.id),
                'name': employee.name or '',
                'cargo': employee.cargo or '',
                'pin': employee.pin or '',
                'active': employee.is_active if hasattr(employee, 'is_active') else True
            }
        })
    
    elif request.method == 'PUT':
        # Actualizar empleado
        # IMPORTANTE: El ID del empleado es INMUTABLE - nunca se puede cambiar
        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            cargo = data.get('cargo', '').strip()
            pin = data.get('pin', '').strip()
            active = data.get('active', True)
            
            # Validar que no se intente cambiar el ID (seguridad adicional)
            if 'id' in data and str(data.get('id')) != str(employee_id):
                return jsonify({
                    'success': False, 
                    'message': 'El ID del trabajador es inmutable y no se puede cambiar'
                }), 400
            
            if not name:
                return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400
            
            # Verificar si ya existe otro empleado local con el mismo nombre
            existing = Employee.query.filter(
                Employee.name == name,
                Employee.id != employee_id,
                
            ).first()
            if existing:
                return jsonify({'success': False, 'message': 'Ya existe otro miembro del equipo con ese nombre'}), 400
            
            # Determinar si es bartender o cajero según el cargo (cargos principales)
            cargo_lower = cargo.lower() if cargo else ''
            is_bartender = 'barra' in cargo_lower or cargo_lower == 'bartender' or cargo_lower == 'coperx'
            is_cashier = cargo_lower == 'caja' or cargo_lower == 'cajero'
            
            # Actualizar campos (el ID NO se toca - es inmutable)
            employee.name = name
            employee.cargo = cargo
            employee.pin = pin if pin else None
            employee.is_active = active
            employee.is_bartender = is_bartender
            employee.is_cashier = is_cashier
            employee.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"Miembro del equipo actualizado: {name} (ID: {employee_id})")
            return jsonify({'success': True, 'message': 'Miembro del equipo actualizado correctamente'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar empleado: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'DELETE':
        # Eliminar cargo (marcar como inactivo) - PROTEGIDO contra eliminación si está en uso
        try:
            data = request.get_json()
            cargo_id = data.get('id')
            
            if not cargo_id:
                return jsonify({'success': False, 'message': 'ID de cargo requerido'}), 400
            
            cargo = Cargo.query.get(cargo_id)
            if not cargo:
                return jsonify({'success': False, 'message': 'Cargo no encontrado'}), 404
            
            # IMPORTANTE: Proteger cargos en uso para no romper informes históricos
            # Verificar todas las referencias al cargo antes de eliminar
            
            # 1. Verificar empleados activos usando este cargo
            empleados_con_cargo = Employee.query.filter_by(cargo=cargo.nombre).count()
            
            # 2. Verificar turnos históricos (EmployeeShift) usando este cargo
            from app.models.employee_shift_models import EmployeeShift
            turnos_con_cargo = EmployeeShift.query.filter_by(cargo=cargo.nombre).count()
            
            # 3. Verificar planillas históricas (PlanillaTrabajador) usando este cargo como rol
            from app.models.jornada_models import PlanillaTrabajador
            planillas_con_cargo = PlanillaTrabajador.query.filter_by(rol=cargo.nombre).count()
            
            # Si hay cualquier referencia, NO permitir eliminar
            total_referencias = empleados_con_cargo + turnos_con_cargo + planillas_con_cargo
            
            if total_referencias > 0:
                mensaje_detalle = []
                if empleados_con_cargo > 0:
                    mensaje_detalle.append(f'{empleados_con_cargo} empleado(s) activo(s)')
                if turnos_con_cargo > 0:
                    mensaje_detalle.append(f'{turnos_con_cargo} turno(s) histórico(s)')
                if planillas_con_cargo > 0:
                    mensaje_detalle.append(f'{planillas_con_cargo} planilla(s) histórica(s)')
                
                mensaje = "No se puede eliminar el cargo "" + cargo.nombre + "" porque está siendo usado por: " + ", ".join(mensaje_detalle) + ". Esto protegería la integridad de los informes históricos."
                
                current_app.logger.warning(
                    f'⚠️  Intento de eliminar cargo en uso: {cargo.nombre} '
                    f'(empleados: {empleados_con_cargo}, turnos: {turnos_con_cargo}, planillas: {planillas_con_cargo})'
                )
                
                return jsonify({
                    'success': False,
                    'message': mensaje,
                    'detalles': {
                        'empleados': empleados_con_cargo,
                        'turnos': turnos_con_cargo,
                        'planillas': planillas_con_cargo
                    }
                }), 400
            
            # Si no hay referencias, marcar como inactivo (soft delete)
            cargo.activo = False
            cargo.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            
            db.session.commit()
            current_app.logger.info(f'✅ Cargo desactivado: {cargo.nombre}')
            return jsonify({'success': True, 'message': 'Cargo eliminado correctamente'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error al eliminar cargo: {e}', exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
            db.session.rollback()
            current_app.logger.error(f"Error al guardar configuración de sueldo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

def require_superadmin():
    """Verifica que el usuario sea el superadmin 'sebagatica'"""
    if require_admin():
        return require_admin()
    
    username = session.get('admin_username', '').lower()
    if username != 'sebagatica':
        return jsonify({
            'success': False, 
            'message': 'Solo el superadministrador puede modificar cargos y sueldos'
        }), 403
    
    return None


@equipo_bp.route('/api/cargo-salaries', methods=['GET', 'POST'])
def api_cargo_salaries():
    """API: Obtener o actualizar sueldos por cargo"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    if request.method == 'GET':
        # Obtener todas las configuraciones de sueldos por cargo
        try:
            configs = CargoSalaryConfig.query.all()
            salaries = {}
            for config in configs:
                salaries[config.cargo] = {
                    'sueldo_por_turno': float(config.sueldo_por_turno),
                    'bono_fijo': float(config.bono_fijo)
                }
            
            return jsonify({
                'success': True,
                'salaries': salaries
            })
        except Exception as e:
            current_app.logger.error(f"Error al obtener sueldos por cargo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        # Verificar que sea superadmin
        if require_superadmin():
            return require_superadmin()
        
        # Actualizar sueldos por cargo
        try:
            from app.models.cargo_audit_models import CargoSalaryAuditLog
            import json as json_lib
            
            data = request.get_json()
            if not isinstance(data, dict):
                return jsonify({'success': False, 'message': 'Datos inválidos'}), 400
            
            username = session.get('admin_username', 'unknown')
            cargos = ['BARRA', 'COPERX', 'CAJA', 'GUARDIA', 'ANFITRIONA', 'ASEO', 'GUARDARROP', 'TÉCNICA', 'DRAG', 'DJ', 'Supervisor', 'Administrador', 'Otro']
            
            for cargo in cargos:
                cargo_data = data.get(cargo, {})
                sueldo_por_turno = float(cargo_data.get('sueldo_por_turno', 0))
                bono_fijo = float(cargo_data.get('bono_fijo', 0))
                
                if sueldo_por_turno < 0 or bono_fijo < 0:
                    return jsonify({'success': False, 'message': f'Los valores para {cargo} no pueden ser negativos'}), 400
                
                config = CargoSalaryConfig.query.filter_by(cargo=cargo).first()
                
                # Guardar valores anteriores para auditoría
                old_values = None
                if config:
                    old_values = {
                        'sueldo_por_turno': float(config.sueldo_por_turno) if config.sueldo_por_turno else 0.0,
                        'bono_fijo': float(config.bono_fijo) if config.bono_fijo else 0.0
                    }
                
                if config:
                    # Actualizar
                    new_values = {
                        'sueldo_por_turno': sueldo_por_turno,
                        'bono_fijo': bono_fijo
                    }
                    
                    # Registrar auditoría solo si hay cambios
                    if old_values and (old_values['sueldo_por_turno'] != sueldo_por_turno or old_values['bono_fijo'] != bono_fijo):
                        audit_log = CargoSalaryAuditLog(
                            action='update',
                            entity_type='salary_config',
                            cargo_nombre=cargo,
                            old_values=json_lib.dumps(old_values),
                            new_values=json_lib.dumps(new_values),
                            changed_by=username,
                            changed_by_username=username,
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent', '')[:500]
                        )
                        db.session.add(audit_log)
                    
                    config.sueldo_por_turno = sueldo_por_turno
                    config.bono_fijo = bono_fijo
                    config.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    # Crear
                    new_values = {
                        'sueldo_por_turno': sueldo_por_turno,
                        'bono_fijo': bono_fijo
                    }
                    
                    # Registrar auditoría
                    audit_log = CargoSalaryAuditLog(
                        action='create',
                        entity_type='salary_config',
                        cargo_nombre=cargo,
                        old_values=None,
                        new_values=json_lib.dumps(new_values),
                        changed_by=username,
                        changed_by_username=username,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent', '')[:500]
                    )
                    db.session.add(audit_log)
                    
                    config = CargoSalaryConfig(
                        cargo=cargo,
                        sueldo_por_turno=sueldo_por_turno,
                        bono_fijo=bono_fijo
                    )
                    db.session.add(config)
            
            db.session.commit()
            current_app.logger.info(f"✅ Sueldos por cargo actualizados por {username}")
            return jsonify({'success': True, 'message': 'Sueldos por cargo guardados correctamente'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al guardar sueldos por cargo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/cargos', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_cargos():
    """API: Gestión completa de cargos (CRUD) con sueldos"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    if request.method == 'GET':
        # Listar todos los cargos activos con sus sueldos
        try:
            # Inicializar cargos por defecto si no existen
            _initialize_default_cargos()
            
            cargos = Cargo.query.filter_by(activo=True).order_by(Cargo.orden, Cargo.nombre).all()
            current_app.logger.info(f"📋 API /api/cargos: {len(cargos)} cargos activos encontrados")
            
            if len(cargos) == 0:
                current_app.logger.warning("⚠️ No se encontraron cargos activos. Intentando inicializar...")
                _initialize_default_cargos()
                cargos = Cargo.query.filter_by(activo=True).order_by(Cargo.orden, Cargo.nombre).all()
                current_app.logger.info(f"📋 Después de inicializar: {len(cargos)} cargos activos")
            
            cargos_data = []
            for cargo in cargos:
                try:
                    cargo_dict = cargo.to_dict()
                    # Obtener sueldo del cargo
                    cargo_salary = CargoSalaryConfig.query.filter_by(cargo=cargo.nombre).first()
                    if cargo_salary:
                        cargo_dict['sueldo_por_turno'] = float(cargo_salary.sueldo_por_turno)
                        cargo_dict['bono_fijo'] = float(cargo_salary.bono_fijo)
                    else:
                        cargo_dict['sueldo_por_turno'] = 0.0
                        cargo_dict['bono_fijo'] = 0.0
                    cargos_data.append(cargo_dict)
                except Exception as e:
                    current_app.logger.error(f"Error procesando cargo {cargo.id}: {e}", exc_info=True)
                    continue
            
            current_app.logger.info(f"✅ Retornando {len(cargos_data)} cargos al cliente")
            return jsonify({
                'success': True,
                'cargos': cargos_data
            })
        except Exception as e:
            current_app.logger.error(f"❌ Error al listar cargos: {e}", exc_info=True)
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        # Verificar que sea superadmin
        if require_superadmin():
            return require_superadmin()
        
        # Crear nuevo cargo con sueldo
        try:
            from app.models.cargo_audit_models import CargoSalaryAuditLog
            import json as json_lib
            
            data = request.get_json()
            nombre = data.get('nombre', '').strip()
            descripcion = data.get('descripcion', '').strip()
            orden = int(data.get('orden', 0))
            sueldo_por_turno = float(data.get('sueldo_por_turno', 0))
            bono_fijo = float(data.get('bono_fijo', 0))
            
            username = session.get('admin_username', 'unknown')
            
            if not nombre:
                return jsonify({'success': False, 'message': 'El nombre del cargo es obligatorio'}), 400
            
            # Verificar si ya existe un cargo con ese nombre
            cargo_existente = Cargo.query.filter_by(nombre=nombre).first()
            
            if cargo_existente:
                # Si el cargo existe y está activo, rechazar
                if cargo_existente.activo:
                    return jsonify({'success': False, 'message': f'Ya existe un cargo activo con el nombre "{nombre}"'}), 400
                
                # Si el cargo existe pero está inactivo, REACTIVARLO
                current_app.logger.info(f"🔄 Reactivando cargo inactivo: {nombre}")
                cargo_existente.activo = True
                cargo_existente.descripcion = descripcion if descripcion else cargo_existente.descripcion
                cargo_existente.orden = orden if orden > 0 else cargo_existente.orden
                cargo_existente.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Actualizar o crear configuración de sueldo
                cargo_salary = CargoSalaryConfig.query.filter_by(cargo=nombre).first()
                if cargo_salary:
                    cargo_salary.sueldo_por_turno = sueldo_por_turno
                    cargo_salary.bono_fijo = bono_fijo
                    cargo_salary.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    cargo_salary = CargoSalaryConfig(
                        cargo=nombre,
                        sueldo_por_turno=sueldo_por_turno,
                        bono_fijo=bono_fijo
                    )
                    db.session.add(cargo_salary)
                
                db.session.commit()
                current_app.logger.info(f"✅ Cargo reactivado: {nombre}")
                return jsonify({
                    'success': True,
                    'message': f'Cargo "{nombre}" reactivado correctamente',
                    'cargo': cargo_existente.to_dict()
                })
            
            # Si no existe, crear uno nuevo
            
            nuevo_cargo = Cargo(
                nombre=nombre,
                descripcion=descripcion,
                activo=True,
                orden=orden
            )
            db.session.add(nuevo_cargo)
            
            # Crear configuración de sueldo
            cargo_salary = CargoSalaryConfig(
                cargo=nombre,
                sueldo_por_turno=sueldo_por_turno,
                bono_fijo=bono_fijo
            )
            db.session.add(cargo_salary)
            
            db.session.commit()
            current_app.logger.info(f"✅ Cargo creado: {nombre}")
            return jsonify({'success': True, 'message': 'Cargo creado correctamente', 'cargo': nuevo_cargo.to_dict()})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear cargo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'PUT':
        # Verificar que sea superadmin
        if require_superadmin():
            return require_superadmin()
        
        # Actualizar cargo y su sueldo
        try:
            from app.models.cargo_audit_models import CargoSalaryAuditLog
            import json as json_lib
            
            data = request.get_json()
            cargo_id = data.get('id')
            nombre = data.get('nombre', '').strip()
            descripcion = data.get('descripcion', '').strip()
            orden = int(data.get('orden', 0))
            activo = data.get('activo', True)
            sueldo_por_turno = float(data.get('sueldo_por_turno', 0))
            bono_fijo = float(data.get('bono_fijo', 0))
            
            username = session.get('admin_username', 'unknown')
            
            if not cargo_id:
                return jsonify({'success': False, 'message': 'ID de cargo requerido'}), 400
            
            cargo = Cargo.query.get(cargo_id)
            if not cargo:
                return jsonify({'success': False, 'message': 'Cargo no encontrado'}), 404
            
            nombre_anterior = cargo.nombre
            
            # Guardar valores anteriores para auditoría
            old_cargo_values = {
                'nombre': cargo.nombre,
                'descripcion': cargo.descripcion,
                'orden': cargo.orden,
                'activo': cargo.activo
            }
            
            cargo_salary_old = CargoSalaryConfig.query.filter_by(cargo=cargo.nombre).first()
            old_salary_values = None
            if cargo_salary_old:
                old_salary_values = {
                    'sueldo_por_turno': float(cargo_salary_old.sueldo_por_turno) if cargo_salary_old.sueldo_por_turno else 0.0,
                    'bono_fijo': float(cargo_salary_old.bono_fijo) if cargo_salary_old.bono_fijo else 0.0
                }
            
            # Verificar si el nuevo nombre ya existe (si cambió)
            if nombre and nombre != cargo.nombre:
                cargo_existente = Cargo.query.filter_by(nombre=nombre).first()
                if cargo_existente:
                    return jsonify({'success': False, 'message': f'Ya existe un cargo con el nombre "{nombre}"'}), 400
                
                # Actualizar nombre en CargoSalaryConfig si existe
                cargo_salary = CargoSalaryConfig.query.filter_by(cargo=nombre_anterior).first()
                if cargo_salary:
                    cargo_salary.cargo = nombre
                    cargo_salary.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Verificar si hay cambios en el cargo
            cargo_changed = (
                (nombre and nombre != cargo.nombre) or
                descripcion != cargo.descripcion or
                orden != cargo.orden or
                activo != cargo.activo
            )
            
            cargo.nombre = nombre if nombre else cargo.nombre
            cargo.descripcion = descripcion
            cargo.orden = orden
            cargo.activo = activo
            cargo.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Registrar auditoría de cargo si hay cambios
            if cargo_changed:
                new_cargo_values = {
                    'nombre': cargo.nombre,
                    'descripcion': cargo.descripcion,
                    'orden': cargo.orden,
                    'activo': cargo.activo
                }
                audit_log_cargo = CargoSalaryAuditLog(
                    action='update',
                    entity_type='cargo',
                    cargo_nombre=nombre_anterior,
                    old_values=json_lib.dumps(old_cargo_values),
                    new_values=json_lib.dumps(new_cargo_values),
                    changed_by=username,
                    changed_by_username=username,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:500]
                )
                db.session.add(audit_log_cargo)
            
            # Actualizar o crear sueldo
            cargo_salary = CargoSalaryConfig.query.filter_by(cargo=cargo.nombre).first()
            salary_changed = False
            if cargo_salary:
                # Verificar si hay cambios en el sueldo
                old_sueldo = float(cargo_salary.sueldo_por_turno) if cargo_salary.sueldo_por_turno else 0.0
                old_bono = float(cargo_salary.bono_fijo) if cargo_salary.bono_fijo else 0.0
                salary_changed = (old_sueldo != sueldo_por_turno or old_bono != bono_fijo)
                
                cargo_salary.sueldo_por_turno = sueldo_por_turno
                cargo_salary.bono_fijo = bono_fijo
                cargo_salary.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            else:
                salary_changed = True
                cargo_salary = CargoSalaryConfig(
                    cargo=cargo.nombre,
                    sueldo_por_turno=sueldo_por_turno,
                    bono_fijo=bono_fijo
                )
                db.session.add(cargo_salary)
            
            # Registrar auditoría de sueldo si hay cambios
            if salary_changed:
                new_salary_values = {
                    'sueldo_por_turno': sueldo_por_turno,
                    'bono_fijo': bono_fijo
                }
                audit_log_salary = CargoSalaryAuditLog(
                    action='update',
                    entity_type='salary_config',
                    cargo_nombre=cargo.nombre,
                    old_values=json_lib.dumps(old_salary_values) if old_salary_values else None,
                    new_values=json_lib.dumps(new_salary_values),
                    changed_by=username,
                    changed_by_username=username,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:500]
                )
                db.session.add(audit_log_salary)
            
            db.session.commit()
            current_app.logger.info(f"✅ Cargo actualizado: {cargo.nombre} por {username}")
            return jsonify({'success': True, 'message': 'Cargo actualizado correctamente', 'cargo': cargo.to_dict()})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar cargo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'DELETE':
        # Verificar que sea superadmin
        if require_superadmin():
            return require_superadmin()
        
        # Eliminar cargo (marcar como inactivo)
        try:
            from app.models.cargo_audit_models import CargoSalaryAuditLog
            import json as json_lib
            
            data = request.get_json()
            cargo_id = data.get('id')
            username = session.get('admin_username', 'unknown')
            
            if not cargo_id:
                return jsonify({'success': False, 'message': 'ID de cargo requerido'}), 400
            
            cargo = Cargo.query.get(cargo_id)
            if not cargo:
                return jsonify({'success': False, 'message': 'Cargo no encontrado'}), 404
            
            # Guardar valores anteriores para auditoría
            old_cargo_values = {
                'nombre': cargo.nombre,
                'descripcion': cargo.descripcion,
                'orden': cargo.orden,
                'activo': cargo.activo
            }
            
            # Verificar si hay empleados usando este cargo
            empleados_con_cargo = Employee.query.filter_by(cargo=cargo.nombre).count()
            # IMPORTANTE: Proteger cargos en uso para no romper informes históricos
            # Verificar todas las referencias al cargo antes de eliminar
            
            # 2. Verificar turnos históricos (EmployeeShift) usando este cargo
            from app.models.employee_shift_models import EmployeeShift
            planillas_con_cargo = PlanillaTrabajador.query.filter_by(rol=cargo.nombre).count()
            
            # Si hay cualquier referencia, NO permitir eliminar
            total_referencias = empleados_con_cargo + turnos_con_cargo + planillas_con_cargo
            
            if total_referencias > 0:
                mensaje_detalle = []
                if empleados_con_cargo > 0:
                    mensaje_detalle.append(f"{empleados_con_cargo} empleado(s) activo(s)")
                if turnos_con_cargo > 0:
                    mensaje_detalle.append(f"{turnos_con_cargo} turno(s) histórico(s)")
                if planillas_con_cargo > 0:
                    mensaje_detalle.append(f"{planillas_con_cargo} planilla(s) histórica(s)")
                mensaje = "No se puede eliminar el cargo "" + cargo.nombre + "" porque está siendo usado por: " + ", ".join(mensaje_detalle) + ". Esto protegería la integridad de los informes históricos."
                mensaje = "No se puede eliminar el cargo "" + cargo.nombre + "" porque está siendo usado por: " + ", ".join(mensaje_detalle) + ". Esto protegería la integridad de los informes históricos."
                
                current_app.logger.warning(
                    f"⚠️  Intento de eliminar cargo en uso: {cargo.nombre} "
                    f"(empleados: {empleados_con_cargo}, turnos: {turnos_con_cargo}, planillas: {planillas_con_cargo})"
                )
                
                return jsonify({
                    "success": False,
                    "message": mensaje,
                    "detalles": {
                        "empleados": empleados_con_cargo,
                        "turnos": turnos_con_cargo,
                        "planillas": planillas_con_cargo
                    }
                }), 400
            if empleados_con_cargo > 0:
                return jsonify({
                    'success': False, 
                    "message": "No se puede eliminar el cargo "" + cargo.nombre + "" porque " + str(empleados_con_cargo) + " empleado(s) lo están usando"
                }), 400
            
            # Marcar como inactivo en lugar de eliminar
            cargo.activo = False
            cargo.updated_at = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            
            db.session.commit()
            current_app.logger.info(f"✅ Cargo desactivado: {cargo.nombre}")
            return jsonify({'success': True, 'message': 'Cargo eliminado correctamente'})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al eliminar cargo: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/shifts/<int:shift_id>/marcar-pagado', methods=['POST'])
def api_marcar_shift_pagado(shift_id):
    """API: Marcar un turno como pagado"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        from app.models.audit_log_models import AuditLog
        from sqlalchemy import select
        import json
        
        # Usar transacción con lock de fila
        with db.session.begin():
            # Obtener turno con lock para evitar race conditions
            shift = db.session.execute(
                select(EmployeeShift)
                .where(EmployeeShift.id == shift_id)
                .with_for_update()  # Lock de fila
            ).scalar_one_or_none()
            
            if not shift:
                return jsonify({'success': False, 'message': 'Turno no encontrado'}), 404
            
            # Validar que no esté ya pagado (doble verificación)
            if shift.pagado:
                return jsonify({
            # IMPORTANTE: El sueldo debe quedar FIJO cuando se marca como pagado
            # Esto asegura que aunque el cargo cambie de sueldo en el futuro,
            # el valor pagado en este momento queda congelado para siempre
                    'success': False,
                    'message': 'Este turno ya está marcado como pagado'
                }), 400
            
            # CORRECCIÓN: Usar Decimal para validación de monto
            from app.helpers.financial_utils import to_decimal
            sueldo_turno_decimal = to_decimal(shift.sueldo_turno)
            sueldo_turno = float(sueldo_turno_decimal)
            if sueldo_turno <= 0:
                return jsonify({
                    'success': False,
                    'message': 'El turno tiene un sueldo inválido'
                }), 400
            
            # Guardar valor antiguo para auditoría
            old_value = json.dumps({
                'pagado': False,
                'fecha_pago': None,
                'sueldo_turno': sueldo_turno
            })
            
            # CORRECCIÓN: Refrescar antes de marcar como pagado para verificar nuevamente
            db.session.refresh(shift)
            if shift.pagado:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': 'Este turno ya fue marcado como pagado por otro proceso'
                }), 400
            
            # Marcar como pagado
            now_utc = datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None)
            shift.pagado = True
            shift.fecha_pago = now_utc
            
            # Registrar en auditoría
            audit_log = AuditLog(
                user_id=session.get('admin_username', 'unknown'),
                username=session.get('admin_username', 'unknown'),
                action='marcar_pago',
                entity_type='EmployeeShift',
                entity_id=str(shift_id),
                old_value=old_value,
                new_value=json.dumps({
                    'pagado': True,
                    'fecha_pago': now_utc.isoformat(),
                    'sueldo_turno': sueldo_turno
                }),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                request_method=request.method,
                request_path=request.path,
                success=True
            )
            db.session.add(audit_log)
        
        # Commit se hace automáticamente
        
        current_app.logger.info(
            f"💰 Turno {shift_id} marcado como pagado para {shift.employee_name} "
            f"(Fecha: {shift.fecha_turno}, Sueldo: ${sueldo_turno:.0f}) "
            f"por {session.get('admin_username', 'unknown')}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Turno marcado como pagado correctamente',
            'shift': shift.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al marcar turno como pagado: {e}", exc_info=True)
        
        # Registrar error en auditoría
        try:
            from app.models.audit_log_models import AuditLog
            error_audit = AuditLog(
                user_id=session.get('admin_username', 'unknown'),
                username=session.get('admin_username', 'unknown'),
                action='marcar_pago',
                entity_type='EmployeeShift',
                entity_id=str(shift_id),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                request_method=request.method,
                request_path=request.path,
                success=False,
                error_message=str(e)
            )
            db.session.add(error_audit)
            db.session.commit()
        except:
            pass
        
        return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/shifts/<int:shift_id>/desmarcar-pagado', methods=['POST'])
def api_desmarcar_shift_pagado(shift_id):
    """API: Desmarcar un turno como pagado"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        shift = EmployeeShift.query.get(shift_id)
        if not shift:
            return jsonify({'success': False, 'message': 'Turno no encontrado'}), 404
        
        # Desmarcar como pagado
        shift.pagado = False
        shift.fecha_pago = None
        
        db.session.commit()
        
        current_app.logger.info(
            f"↩️ Turno {shift_id} desmarcado como pagado para {shift.employee_name} "
            f"(Fecha: {shift.fecha_turno})"
        )
        
        return jsonify({
            'success': True,
            'message': 'Turno desmarcado correctamente',
            'shift': shift.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al desmarcar turno: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/advances/<employee_id>', methods=['GET', 'POST'])
def api_advances(employee_id):
    """API: Obtener o crear abonos/pagos excepcionales para un empleado"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        # Validación mejorada de employee_id
        from app.helpers.validation import validate_employee_id, validate_amount
        
        is_valid_emp_id, emp_id_error = validate_employee_id(employee_id)
        if not is_valid_emp_id:
            return jsonify({'success': False, 'message': f'ID de empleado inválido: {emp_id_error}'}), 400
        
        # Validar monto si se proporciona
        monto = request.json.get('monto') if request.json else None
        if monto is not None:
            is_valid_amount, monto_float, amount_error = validate_amount(str(monto), min_amount=0.01, max_amount=10000000.0)
            if not is_valid_amount:
                return jsonify({'success': False, 'message': f'Monto inválido: {amount_error}'}), 400
        
        # Verificar que el empleado existe
        employee = Employee.query.filter(
            Employee.id == str(employee_id),
            
        ).first()
        
        if not employee:
            return jsonify({'success': False, 'message': 'Empleado no encontrado'}), 404
        
        if request.method == 'GET':
            # Obtener todos los abonos del empleado
            abonos = EmployeeAdvance.query.filter_by(employee_id=employee_id).order_by(
                EmployeeAdvance.fecha_abono.desc(),
                EmployeeAdvance.created_at.desc()
            ).all()
            
            return jsonify({
                'success': True,
                'advances': [a.to_dict() for a in abonos]
            })
        
        elif request.method == 'POST':
            # Crear nuevo abono
            data = request.get_json()
            
            tipo = data.get('tipo', 'pago_excepcional')
            monto = float(data.get('monto', 0))
            descripcion = data.get('descripcion', '')
            fecha_abono = data.get('fecha_abono', datetime.now(CHILE_TZ).strftime('%Y-%m-%d'))
            notas = data.get('notas', '')
            
            if monto == 0:
                return jsonify({'success': False, 'message': 'El monto no puede ser cero'}), 400
            
            # Crear abono
            # Validar que el abono no exceda el sueldo pendiente
            from app.models.employee_shift_models import EmployeeShift
            from sqlalchemy import func
            
            sueldo_pendiente = db.session.query(
                func.sum(EmployeeShift.sueldo_turno)
            ).filter_by(
                employee_id=str(employee_id),
                pagado=False
            ).scalar() or 0
            
            abonos_pendientes = db.session.query(
                func.sum(EmployeeAdvance.monto)
            ).filter_by(
                employee_id=str(employee_id),
                aplicado=False
            ).scalar() or 0
            
            disponible = float(sueldo_pendiente) - float(abonos_pendientes)
            
            if float(monto) > disponible:
                return jsonify({
                    'success': False,
                    'message': f'El abono (${float(monto):,.0f}) excede el sueldo disponible (${disponible:,.0f})'
                }), 400
            
            # Validar y sanitizar descripción y notas
            if descripcion:
                descripcion = descripcion.strip()[:500]
            if notas:
                notas = notas.strip()[:1000]
            
            abono = EmployeeAdvance(
                employee_id=str(employee_id),
                employee_name=employee.name or 'Sin nombre',
                tipo=tipo,
                monto=monto,
                descripcion=descripcion,
                fecha_abono=fecha_abono,
                aplicado=False,
                creado_por=session.get('admin_username', 'Admin'),
                notas=notas
            )
            
            db.session.add(abono)
            db.session.commit()
            
            current_app.logger.info(
                f"💰 Abono creado para {employee.name}: ${monto:.0f} ({tipo}) - {descripcion}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Abono creado correctamente',
                'advance': abono.to_dict()
            })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en API de abonos: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@equipo_bp.route('/api/advances/<employee_id>/<int:advance_id>', methods=['DELETE'])
def api_delete_advance(employee_id, advance_id):
    """API: Eliminar un abono (solo si no está aplicado)"""
    if require_admin():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        abono = EmployeeAdvance.query.filter_by(
            id=advance_id,
            employee_id=employee_id
        ).first()
        
        if not abono:
            return jsonify({'success': False, 'message': 'Abono no encontrado'}), 404
        
        if abono.aplicado:
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar un abono que ya fue aplicado'
            }), 400
        
        monto = float(abono.monto or 0)
        employee_name = abono.employee_name
        
        db.session.delete(abono)
        db.session.commit()
        
        current_app.logger.info(
            f"🗑️ Abono eliminado para {employee_name}: ${monto:.0f} ({abono.tipo})"
        )
        
        return jsonify({
            'success': True,
            'message': 'Abono eliminado correctamente'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar abono: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

