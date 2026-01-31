"""
Rutas para log de auditoría de caja SUPERADMIN
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models.superadmin_sale_audit_models import SuperadminSaleAudit
from app.models import db
from sqlalchemy import desc
from datetime import datetime, timedelta

superadmin_audit_bp = Blueprint('superadmin_audit', __name__)


@superadmin_audit_bp.route('/admin/superadmin/audit')
def admin_superadmin_audit():
    """Vista de log de auditoría de caja SUPERADMIN (solo superadmin)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Verificar si es superadmin
    username = session.get('admin_username', '').lower()
    is_superadmin = (username == 'sebagatica')
    
    if not is_superadmin:
        flash('No tienes autorización para ver este log', 'error')
        return redirect(url_for('routes.admin_dashboard'))
    
    try:
        # Obtener parámetros de filtrado
        tipo_operacion = request.args.get('tipo_operacion', '')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Construir query
        query = SuperadminSaleAudit.query
        
        if tipo_operacion:
            query = query.filter(SuperadminSaleAudit.tipo_operacion == tipo_operacion)
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(SuperadminSaleAudit.created_at >= fecha_desde_dt)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(SuperadminSaleAudit.created_at < fecha_hasta_dt)
            except ValueError:
                pass
        
        # Ordenar por fecha descendente
        query = query.order_by(desc(SuperadminSaleAudit.created_at))
        
        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        audit_logs = pagination.items
        
        # Estadísticas
        total_cortesias = SuperadminSaleAudit.query.filter_by(tipo_operacion='CORTESIA').count()
        total_pruebas = SuperadminSaleAudit.query.filter_by(tipo_operacion='PRUEBA_DEPLOY').count()
        
        return render_template(
            'admin/superadmin_audit.html',
            audit_logs=audit_logs,
            pagination=pagination,
            tipo_operacion=tipo_operacion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            total_cortesias=total_cortesias,
            total_pruebas=total_pruebas
        )
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error al cargar log de auditoría: {e}", exc_info=True)
        flash(f'Error al cargar log: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))











