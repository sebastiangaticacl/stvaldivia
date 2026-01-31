"""
Rutas para gestión de turnos de bartenders
Apertura y cierre de turnos con control de stock tipo "caja ciega"
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.helpers.turnos_bartender import get_turnos_bartender_helper
from app.helpers.inventario_turno import get_inventario_turno_helper
from app.helpers.alertas_turno import get_alertas_turno_helper
from app.models.bartender_turno_models import BartenderTurno
from app.models.inventory_stock_models import Ingredient
from app.models import db

bartender_turnos_bp = Blueprint('bartender_turnos', __name__, url_prefix='/bartender/turnos')


@bartender_turnos_bp.route('/abrir', methods=['GET', 'POST'])
def abrir_turno():
    """Abrir un nuevo turno de bartender"""
    # Verificar sesión de bartender
    if 'bartender' not in session:
        flash("Por favor, inicia sesión como bartender.", "info")
        return redirect(url_for('scanner.seleccionar_bartender'))
    
    # Obtener información del bartender de forma consistente
    bartender_id = session.get('bartender_id')
    bartender_name = session.get('bartender', 'Desconocido')
    # Si no hay bartender_id pero sí bartender, usar el nombre como ID temporal
    if not bartender_id and bartender_name:
        bartender_id = bartender_name
    
    helper = get_turnos_bartender_helper()
    
    if request.method == 'POST':
        ubicacion = request.form.get('ubicacion')
        observaciones = request.form.get('observaciones', '')
        
        # Obtener stock inicial del formulario
        stock_inicial = []
        for key, value in request.form.items():
            if key.startswith('stock_'):
                insumo_id = int(key.replace('stock_', ''))
                cantidad = float(value) if value else 0.0
                if cantidad > 0:
                    stock_inicial.append({
                        'insumo_id': insumo_id,
                        'cantidad': cantidad
                    })
        
        if not stock_inicial:
            flash("Debes ingresar al menos un insumo con stock inicial.", "error")
            return redirect(url_for('bartender_turnos.abrir_turno'))
        
        # Abrir turno
        success, message, turno = helper.abrir_turno(
            bartender_id=bartender_id,
            bartender_name=bartender_name,
            ubicacion=ubicacion,
            stock_inicial=stock_inicial,
            observaciones=observaciones
        )
        
        if success:
            flash(message, "success")
            return redirect(url_for('bartender_turnos.ver_turno', turno_id=turno.id))
        else:
            flash(message, "error")
            return redirect(url_for('bartender_turnos.abrir_turno'))
    
    # GET: Mostrar formulario de apertura
    ubicacion = request.args.get('ubicacion', 'barra_pista')
    
    # Obtener stock sugerido
    stock_sugerido = helper.get_stock_sugerido(ubicacion)
    
    # Verificar si ya hay un turno abierto
    turno_abierto = helper.get_turno_abierto(bartender_id, ubicacion)
    
    return render_template(
        'bartender_turnos/abrir_turno.html',
        ubicacion=ubicacion,
        stock_sugerido=stock_sugerido,
        turno_abierto=turno_abierto
    )


@bartender_turnos_bp.route('/turno/<int:turno_id>')
def ver_turno(turno_id):
    """Ver detalles de un turno"""
    turno = BartenderTurno.query.get_or_404(turno_id)
    
    # Verificar permisos (solo el bartender o admin)
    if 'bartender' in session:
        bartender_id = session.get('bartender_id') or session.get('bartender', 'unknown')
        if turno.bartender_id != bartender_id and not session.get('admin_logged_in'):
            flash("No tienes permiso para ver este turno.", "error")
            return redirect(url_for('scanner.scanner'))
    
    # Obtener stock inicial y final
    stock_inicial = {s.insumo_id: s for s in turno.stock_inicial}
    stock_final = {s.insumo_id: s for s in turno.stock_final}
    
    # Obtener desviaciones si el turno está cerrado
    desviaciones = []
    alertas = []
    resumen_financiero = {}
    
    if turno.estado == 'cerrado':
        inventario_helper = get_inventario_turno_helper()
        alertas_helper = get_alertas_turno_helper()
        
        desviaciones = turno.desviaciones
        alertas = alertas_helper.get_alertas_turno(turno_id)
        resumen_financiero = inventario_helper.calcular_resumen_financiero_turno(turno_id)
    
    return render_template(
        'bartender_turnos/ver_turno.html',
        turno=turno,
        stock_inicial=stock_inicial,
        stock_final=stock_final,
        desviaciones=desviaciones,
        alertas=alertas,
        resumen_financiero=resumen_financiero
    )


@bartender_turnos_bp.route('/turno/<int:turno_id>/cerrar', methods=['GET', 'POST'])
def cerrar_turno(turno_id):
    """Cerrar un turno"""
    turno = BartenderTurno.query.get_or_404(turno_id)
    
    # Verificar permisos
    if 'bartender' in session:
        bartender_id = session.get('bartender_id') or session.get('bartender', 'unknown')
        if turno.bartender_id != bartender_id and not session.get('admin_logged_in'):
            flash("No tienes permiso para cerrar este turno.", "error")
            return redirect(url_for('bartender_turnos.ver_turno', turno_id=turno_id))
    
    if turno.estado != 'abierto':
        flash(f"El turno ya está {turno.estado}.", "error")
        return redirect(url_for('bartender_turnos.ver_turno', turno_id=turno_id))
    
    helper = get_turnos_bartender_helper()
    inventario_helper = get_inventario_turno_helper()
    alertas_helper = get_alertas_turno_helper()
    
    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        
        # Obtener stock final del formulario
        stock_final = []
        for key, value in request.form.items():
            if key.startswith('stock_final_'):
                insumo_id = int(key.replace('stock_final_', ''))
                cantidad = float(value) if value else 0.0
                stock_final.append({
                    'insumo_id': insumo_id,
                    'cantidad': cantidad
                })
        
        # Cerrar turno
        success, message, turno_cerrado = helper.cerrar_turno(
            turno_id=turno_id,
            stock_final=stock_final,
            observaciones=observaciones
        )
        
        if success:
            # Calcular desviaciones
            inventario_helper.calcular_desviaciones_turno(turno_id)
            
            # Detectar alertas
            alertas_helper.detectar_alertas_turno(turno_id)
            
            # Calcular resumen completo del turno (guarda todos los valores en el turno)
            resumen_success, resumen_message = helper.calcular_resumen_turno(turno_cerrado)
            
            if not resumen_success:
                current_app.logger.warning(f"⚠️ Error al calcular resumen: {resumen_message}")
                flash(f"Turno cerrado pero hubo un problema al calcular el resumen: {resumen_message}", "warning")
            else:
                flash(message, "success")
            
            # Recargar turno para obtener valores actualizados
            db.session.refresh(turno_cerrado)
            
            return redirect(url_for('bartender_turnos.resumen_turno', turno_id=turno_id))
        else:
            flash(message, "error")
            return redirect(url_for('bartender_turnos.cerrar_turno', turno_id=turno_id))
    
    # GET: Mostrar formulario de cierre
    # Obtener stock inicial para mostrar
    stock_inicial = {s.insumo_id: s for s in turno.stock_inicial}
    
    # Obtener insumos con sus nombres
    insumos = {}
    for stock in turno.stock_inicial:
        insumo = Ingredient.query.get(stock.insumo_id)
        if insumo:
            insumos[stock.insumo_id] = insumo
    
    return render_template(
        'bartender_turnos/cerrar_turno.html',
        turno=turno,
        stock_inicial=stock_inicial,
        insumos=insumos
    )


@bartender_turnos_bp.route('/mis_turnos')
def mis_turnos():
    """Listar turnos del bartender actual"""
    if 'bartender' not in session:
        flash("Por favor, inicia sesión como bartender.", "info")
        return redirect(url_for('scanner.seleccionar_bartender'))
    
    bartender_id = session.get('bartender_id') or session.get('bartender', 'unknown')
    
    turnos = BartenderTurno.query.filter_by(bartender_id=bartender_id).order_by(
        BartenderTurno.fecha_hora_apertura.desc()
    ).limit(50).all()
    
    return render_template('bartender_turnos/mis_turnos.html', turnos=turnos)


@bartender_turnos_bp.route('/turno/<int:turno_id>/resumen.json')
def resumen_turno_json(turno_id):
    """Endpoint JSON: Obtener resumen completo del turno"""
    turno = BartenderTurno.query.get_or_404(turno_id)
    
    # Obtener alertas de fuga
    from app.helpers.alertas_turno import get_alertas_turno_helper
    alertas_helper = get_alertas_turno_helper()
    alertas = alertas_helper.get_alertas_turno(turno_id)
    
    # Obtener nombres de insumos para las alertas
    from app.models.inventory_stock_models import Ingredient
    alertas_data = []
    for alerta in alertas:
        insumo = Ingredient.query.get(alerta.insumo_id)
        alertas_data.append({
            'insumo': insumo.name if insumo else f"Insumo {alerta.insumo_id}",
            'insumo_id': alerta.insumo_id,
            'ubicacion': alerta.ubicacion,
            'diferencia_turno': float(alerta.diferencia_turno) if alerta.diferencia_turno else 0.0,
            'diferencia_porcentual_turno': float(alerta.diferencia_porcentual_turno) if alerta.diferencia_porcentual_turno else 0.0,
            'costo_diferencia': float(alerta.costo_diferencia) if alerta.costo_diferencia else 0.0,
            'criticidad': alerta.criticidad,
            'atendida': alerta.atendida,
            'fecha_hora': alerta.fecha_hora.isoformat() if alerta.fecha_hora else None
        })
    
    return jsonify({
        'id': turno.id,
        'bartender_id': turno.bartender_id,
        'bartender_name': turno.bartender_name,
        'ubicacion': turno.ubicacion,
        'estado': turno.estado,
        'fecha_hora_apertura': turno.fecha_hora_apertura.isoformat() if turno.fecha_hora_apertura else None,
        'fecha_hora_cierre': turno.fecha_hora_cierre.isoformat() if turno.fecha_hora_cierre else None,
        'observaciones_apertura': turno.observaciones_apertura,
        'observaciones_cierre': turno.observaciones_cierre,
        'valor_inicial_barra_costo': float(turno.valor_inicial_barra_costo) if turno.valor_inicial_barra_costo else 0.0,
        'valor_final_barra_costo': float(turno.valor_final_barra_costo) if turno.valor_final_barra_costo else 0.0,
        'valor_vendido_venta': float(turno.valor_vendido_venta) if turno.valor_vendido_venta else 0.0,
        'valor_vendido_costo': float(turno.valor_vendido_costo) if turno.valor_vendido_costo else 0.0,
        'valor_merma_costo': float(turno.valor_merma_costo) if turno.valor_merma_costo else 0.0,
        'valor_perdida_no_justificada_costo': float(turno.valor_perdida_no_justificada_costo) if turno.valor_perdida_no_justificada_costo else 0.0,
        'flag_fuga_critica': turno.flag_fuga_critica,
        'margen_bruto': float(turno.get_margen_bruto()) if turno.get_margen_bruto() else None,
        'margen_bruto_porcentual': float(turno.get_margen_bruto_porcentual()) if turno.get_margen_bruto_porcentual() else None,
        'eficiencia_porcentual': float(turno.get_eficiencia_porcentual()) if turno.get_eficiencia_porcentual() else None,
        'duracion_minutos': turno.get_duracion_minutos(),
        'alertas_fuga': alertas_data,
        'total_alertas': len(alertas_data),
        'alertas_pendientes': sum(1 for a in alertas_data if not a['atendida'])
    })


@bartender_turnos_bp.route('/turno/<int:turno_id>/resumen')
def resumen_turno(turno_id):
    """Vista HTML: Resumen completo del turno para gerencia"""
    turno = BartenderTurno.query.get_or_404(turno_id)
    
    # Verificar permisos (solo bartender del turno o admin)
    if 'bartender' in session:
        bartender_id = session.get('bartender_id') or session.get('bartender', 'unknown')
        if turno.bartender_id != bartender_id and not session.get('admin_logged_in'):
            flash("No tienes permiso para ver este turno.", "error")
            return redirect(url_for('scanner.scanner'))
    
    # Obtener alertas de fuga
    from app.helpers.alertas_turno import get_alertas_turno_helper
    from app.models.inventory_stock_models import Ingredient
    
    alertas_helper = get_alertas_turno_helper()
    alertas = alertas_helper.get_alertas_turno(turno_id)
    
    # Enriquecer alertas con nombres de insumos
    alertas_enriquecidas = []
    for alerta in alertas:
        insumo = Ingredient.query.get(alerta.insumo_id)
        alertas_enriquecidas.append({
            'alerta': alerta,
            'insumo_nombre': insumo.name if insumo else f"Insumo {alerta.insumo_id}"
        })
    
    return render_template(
        'bartender_turnos/resumen_turno.html',
        turno=turno,
        alertas=alertas_enriquecidas
    )


@bartender_turnos_bp.route('/api/stock_sugerido')
def api_stock_sugerido():
    """API: Obtener stock sugerido para una ubicación"""
    ubicacion = request.args.get('ubicacion', 'barra_pista')
    
    helper = get_turnos_bartender_helper()
    stock_sugerido = helper.get_stock_sugerido(ubicacion)
    
    return jsonify({
        'success': True,
        'stock_sugerido': stock_sugerido
    })


@bartender_turnos_bp.route('/resumen_dia')
def resumen_dia():
    """Panel diario de turnos de bartenders para gerencia"""
    from datetime import datetime, date, timedelta
    from sqlalchemy import func, or_, and_
    
    current_app.logger.info(f"📊 Acceso a resumen_dia - Admin logged in: {session.get('admin_logged_in')}")
    
    # Verificar permisos (solo admin o gerencia)
    if not session.get('admin_logged_in'):
        current_app.logger.warning("⚠️ Intento de acceso sin autenticación admin")
        flash("No tienes permiso para ver este panel.", "error")
        return redirect(url_for('auth.login_admin'))
    
    # Obtener parámetros
    fecha_str = request.args.get('fecha', None)
    ubicacion = request.args.get('ubicacion', None)
    
    # Parsear fecha
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Formato de fecha inválido. Use YYYY-MM-DD", "error")
            fecha = date.today()
    else:
        fecha = date.today()
    
    # Construir query base: turnos cerrados que se abrieron o cerraron en esa fecha
    # Usar comparación de datetime para compatibilidad con SQLite y PostgreSQL
    fecha_inicio = datetime.combine(fecha, datetime.min.time())
    fecha_fin = datetime.combine(fecha, datetime.max.time()) + timedelta(days=1)
    
    query = BartenderTurno.query.filter(
        BartenderTurno.estado == 'cerrado',
        or_(
            and_(
                BartenderTurno.fecha_hora_apertura >= fecha_inicio,
                BartenderTurno.fecha_hora_apertura < fecha_fin
            ),
            and_(
                BartenderTurno.fecha_hora_cierre >= fecha_inicio,
                BartenderTurno.fecha_hora_cierre < fecha_fin
            )
        )
    )
    
    # Filtrar por ubicación si se especifica
    if ubicacion:
        query = query.filter(BartenderTurno.ubicacion == ubicacion)
    
    # Ordenar por fecha de cierre (más reciente primero)
    turnos = query.order_by(
        BartenderTurno.fecha_hora_cierre.desc(),
        BartenderTurno.fecha_hora_apertura.desc()
    ).all()
    
    current_app.logger.info(f"📊 Resumen día: fecha={fecha}, ubicacion={ubicacion}, turnos encontrados={len(turnos)}")
    
    # Calcular totales del día
    suma_venta = sum(
        float(t.valor_vendido_venta) if t.valor_vendido_venta else 0.0 
        for t in turnos
    )
    suma_costo = sum(
        float(t.valor_vendido_costo) if t.valor_vendido_costo else 0.0 
        for t in turnos
    )
    suma_merma = sum(
        float(t.valor_merma_costo) if t.valor_merma_costo else 0.0 
        for t in turnos
    )
    suma_perdida_no_justificada = sum(
        float(t.valor_perdida_no_justificada_costo) if t.valor_perdida_no_justificada_costo else 0.0 
        for t in turnos
    )
    cantidad_turnos_con_fuga_critica = sum(
        1 for t in turnos if t.flag_fuga_critica
    )
    
    # Preparar datos para el template
    turnos_data = []
    for turno in turnos:
        turnos_data.append({
            'turno': turno,
            'valor_inicial_barra_costo': float(turno.valor_inicial_barra_costo) if turno.valor_inicial_barra_costo else 0.0,
            'valor_final_barra_costo': float(turno.valor_final_barra_costo) if turno.valor_final_barra_costo else 0.0,
            'valor_vendido_venta': float(turno.valor_vendido_venta) if turno.valor_vendido_venta else 0.0,
            'valor_vendido_costo': float(turno.valor_vendido_costo) if turno.valor_vendido_costo else 0.0,
            'valor_merma_costo': float(turno.valor_merma_costo) if turno.valor_merma_costo else 0.0,
            'valor_perdida_no_justificada_costo': float(turno.valor_perdida_no_justificada_costo) if turno.valor_perdida_no_justificada_costo else 0.0,
            'flag_fuga_critica': turno.flag_fuga_critica,
            'margen_bruto': float(turno.get_margen_bruto()) if turno.get_margen_bruto() else 0.0
        })
    
    # Si es request JSON, retornar JSON
    if request.args.get('format') == 'json' or request.headers.get('Accept') == 'application/json':
        return jsonify({
            'fecha': fecha.isoformat(),
            'ubicacion': ubicacion,
            'total_turnos': len(turnos),
            'turnos': [
                {
                    'id': t['turno'].id,
                    'bartender_name': t['turno'].bartender_name,
                    'ubicacion': t['turno'].ubicacion,
                    'fecha_hora_apertura': t['turno'].fecha_hora_apertura.isoformat() if t['turno'].fecha_hora_apertura else None,
                    'fecha_hora_cierre': t['turno'].fecha_hora_cierre.isoformat() if t['turno'].fecha_hora_cierre else None,
                    'valor_inicial_barra_costo': t['valor_inicial_barra_costo'],
                    'valor_final_barra_costo': t['valor_final_barra_costo'],
                    'valor_vendido_venta': t['valor_vendido_venta'],
                    'valor_vendido_costo': t['valor_vendido_costo'],
                    'valor_merma_costo': t['valor_merma_costo'],
                    'valor_perdida_no_justificada_costo': t['valor_perdida_no_justificada_costo'],
                    'flag_fuga_critica': t['flag_fuga_critica'],
                    'margen_bruto': t['margen_bruto']
                }
                for t in turnos_data
            ],
            'totales': {
                'suma_venta': suma_venta,
                'suma_costo': suma_costo,
                'suma_merma': suma_merma,
                'suma_perdida_no_justificada': suma_perdida_no_justificada,
                'cantidad_turnos_con_fuga_critica': cantidad_turnos_con_fuga_critica,
                'margen_bruto_total': suma_venta - suma_costo
            }
        })
    
    # Retornar vista HTML
    current_app.logger.info(f"📊 Renderizando template con {len(turnos_data)} turnos")
    return render_template(
        'bartender_turnos/resumen_dia.html',
        fecha=fecha,
        fecha_str=fecha.isoformat(),
        ubicacion=ubicacion,
        turnos=turnos_data,
        totales={
            'suma_venta': suma_venta,
            'suma_costo': suma_costo,
            'suma_merma': suma_merma,
            'suma_perdida_no_justificada': suma_perdida_no_justificada,
            'cantidad_turnos_con_fuga_critica': cantidad_turnos_con_fuga_critica,
            'margen_bruto_total': suma_venta - suma_costo
        }
    )





