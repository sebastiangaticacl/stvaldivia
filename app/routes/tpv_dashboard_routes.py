"""
Rutas para dashboard de monitoreo de TPV (Puntos de Venta)
"""
from flask import Blueprint, render_template, jsonify, session, request, redirect
from flask import url_for
from app.models import db
from app.models.pos_models import PosRegister, RegisterSession, PosSale
from app.models.jornada_models import Jornada
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func
import json

tpv_dashboard_bp = Blueprint('tpv_dashboard', __name__, url_prefix='/admin/tpv')


@tpv_dashboard_bp.route('/dashboard')
def dashboard():
    """Dashboard principal de monitoreo de TPV"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener todos los TPV activos
        tpv_list = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.name).all()
        
        # Obtener jornada actual
        jornada_actual = Jornada.query.filter_by(estado_apertura='abierto').order_by(Jornada.fecha.desc()).first()
        
        # Preparar datos de cada TPV
        tpv_data = []
        for tpv in tpv_list:
            # Obtener sesión activa
            active_session = None
            if jornada_actual:
                active_session = RegisterSession.query.filter_by(
                    register_id=str(tpv.id),
                    status='OPEN',
                    jornada_id=jornada_actual.id
                ).first()
            
            # Calcular estadísticas del día
            today = datetime.now().strftime('%Y-%m-%d')
            sales_today = PosSale.query.filter(
                PosSale.register_id == str(tpv.id),
                PosSale.shift_date == today,
                PosSale.is_cancelled == False
            ).all()
            
            total_sales = len(sales_today)
            total_amount = sum(float(sale.total_amount) for sale in sales_today)
            
            tpv_data.append({
                'tpv': tpv,
                'active_session': active_session,
                'total_sales': total_sales,
                'total_amount': total_amount,
                'is_open': active_session is not None
            })
        
        return render_template('admin/tpv/dashboard.html', 
                             tpv_data=tpv_data,
                             jornada_actual=jornada_actual)
    except Exception as e:
        current_app.logger.error(f"Error en dashboard TPV: {e}", exc_info=True)
        return render_template('admin/tpv/dashboard.html', 
                             tpv_data=[],
                             jornada_actual=None,
                             error=str(e))


@tpv_dashboard_bp.route('/api/status')
def api_status():
    """API: Estado de todos los TPV"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        # Obtener jornada actual
        jornada_actual = Jornada.query.filter_by(estado_apertura='abierto').order_by(Jornada.fecha.desc()).first()
        
        tpv_list = PosRegister.query.filter_by(is_active=True).all()
        status_data = []
        
        for tpv in tpv_list:
            # Sesión activa
            active_session = None
            if jornada_actual:
                active_session = RegisterSession.query.filter_by(
                    register_id=str(tpv.id),
                    status='OPEN',
                    jornada_id=jornada_actual.id
                ).first()
            
            # Estadísticas del día
            today = datetime.now().strftime('%Y-%m-%d')
            sales_today = PosSale.query.filter(
                PosSale.register_id == str(tpv.id),
                PosSale.shift_date == today,
                PosSale.is_cancelled == False
            ).all()
            
            status_data.append({
                'id': tpv.id,
                'name': tpv.name,
                'code': tpv.code,
                'location': tpv.location,
                'tpv_type': tpv.tpv_type,
                'is_open': active_session is not None,
                'opened_by': active_session.opened_by_employee_name if active_session else None,
                'opened_at': active_session.opened_at.isoformat() if active_session and active_session.opened_at else None,
                'total_sales': len(sales_today),
                'total_amount': sum(float(sale.total_amount) for sale in sales_today),
            })
        
        return jsonify({
            'success': True,
            'tpv_status': status_data,
            'jornada_actual': {
                'id': jornada_actual.id,
                'fecha': jornada_actual.fecha.isoformat() if jornada_actual and jornada_actual.fecha else None
            } if jornada_actual else None
        })
    except Exception as e:
        current_app.logger.error(f"Error en API status TPV: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@tpv_dashboard_bp.route('/api/<int:tpv_id>/stats')
def api_tpv_stats(tpv_id):
    """API: Estadísticas detalladas de un TPV"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        tpv = PosRegister.query.get_or_404(tpv_id)
        
        # Estadísticas del día
        today = datetime.now().strftime('%Y-%m-%d')
        sales_today = PosSale.query.filter(
            PosSale.register_id == str(tpv.id),
            PosSale.shift_date == today,
            PosSale.is_cancelled == False
        ).all()
        
        # Estadísticas por método de pago
        cash_total = sum(float(sale.payment_cash) for sale in sales_today)
        debit_total = sum(float(sale.payment_debit) for sale in sales_today)
        credit_total = sum(float(sale.payment_credit) for sale in sales_today)
        
        # Estadísticas de la semana
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        sales_week = PosSale.query.filter(
            PosSale.register_id == str(tpv.id),
            PosSale.shift_date >= week_start,
            PosSale.is_cancelled == False
        ).all()
        
        return jsonify({
            'success': True,
            'tpv': {
                'id': tpv.id,
                'name': tpv.name,
                'code': tpv.code,
                'location': tpv.location,
                'tpv_type': tpv.tpv_type
            },
            'today': {
                'total_sales': len(sales_today),
                'total_amount': sum(float(sale.total_amount) for sale in sales_today),
                'cash': cash_total,
                'debit': debit_total,
                'credit': credit_total
            },
            'week': {
                'total_sales': len(sales_week),
                'total_amount': sum(float(sale.total_amount) for sale in sales_week)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error en API stats TPV: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

