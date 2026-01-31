"""
API V1 Operational - Endpoints internos para datos operativos
Pensada para bot de IA, dashboards internos y futuros servicios
"""
import os
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, date
from sqlalchemy import func, and_
from app.models import db
from app.models.pos_models import PosSale, PosSaleItem
from app.models.delivery_models import Delivery, FraudAttempt
from app.helpers.timezone_utils import CHILE_TZ

operational_api = Blueprint("operational_api", __name__, url_prefix="/api/v1/operational")


def log_api_access(endpoint: str, method: str, status_code: int):
    """
    Registra acceso a API operational.
    NO registra API keys ni payloads sensibles.
    """
    try:
        remote_addr = request.remote_addr or 'unknown'
        timestamp = datetime.utcnow()
        
        current_app.logger.info(
            f"API_OPERATIONAL_ACCESS: endpoint={endpoint} method={method} "
            f"remote_addr={remote_addr} status_code={status_code} timestamp={timestamp.isoformat()}"
        )
    except Exception as e:
        # No fallar si el logging falla
        current_app.logger.warning(f"Error al registrar acceso API operational: {e}")


def require_internal_api_key():
    """
    Verifica que el request tenga el header X-API-KEY válido.
    Retorna None si es válido, o una respuesta JSON con error 401 si no.
    """
    api_key = request.headers.get('X-API-KEY')
    valid_key = os.environ.get('BIMBA_INTERNAL_API_KEY')
    
    if not valid_key:
        current_app.logger.warning("BIMBA_INTERNAL_API_KEY no configurada en variables de entorno")
        return jsonify({
            "status": "unauthorized",
            "detalle": "API key no configurada en el servidor"
        }), 401
    
    if not api_key or api_key != valid_key:
        return jsonify({
            "status": "unauthorized",
            "detalle": "API key inválida o faltante"
        }), 401
    
    return None


def parse_date(date_str):
    """
    Parsea una fecha en formato YYYY-MM-DD o retorna la fecha de hoy.
    """
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    return datetime.now(CHILE_TZ).date()


@operational_api.route('/sales/summary', methods=['GET'])
def sales_summary():
    """
    Endpoint: Resumen de ventas del día
    """
    auth_check = require_internal_api_key()
    if auth_check:
        log_api_access('/sales/summary', 'GET', 401)
        return auth_check
    
    try:
        date_str = request.args.get('date')
        target_date = parse_date(date_str)
        date_str = target_date.strftime('%Y-%m-%d')
        
        sales_query = PosSale.query.filter(PosSale.shift_date == date_str)
        
        total_sales = sales_query.count()
        
        total_revenue = db.session.query(
            func.sum(PosSale.total_amount)
        ).filter(PosSale.shift_date == date_str).scalar() or 0.0
        
        payment_methods = db.session.query(
            func.sum(PosSale.payment_cash).label('cash'),
            func.sum(PosSale.payment_debit).label('debit'),
            func.sum(PosSale.payment_credit).label('credit')
        ).filter(PosSale.shift_date == date_str).first()
        
        by_register = db.session.query(
            PosSale.register_id,
            PosSale.register_name,
            func.count(PosSale.id).label('sales'),
            func.sum(PosSale.total_amount).label('revenue')
        ).filter(
            PosSale.shift_date == date_str
        ).group_by(
            PosSale.register_id,
            PosSale.register_name
        ).all()
        
        by_payment_method = {
            "cash": float(payment_methods.cash) if payment_methods and payment_methods.cash else 0.0,
            "debit": float(payment_methods.debit) if payment_methods and payment_methods.debit else 0.0,
            "credit": float(payment_methods.credit) if payment_methods and payment_methods.credit else 0.0,
            "transfer": 0.0,
            "other": 0.0
        }
        
        by_register_list = [
            {
                "register_id": reg.register_id,
                "register_name": reg.register_name,
                "sales": reg.sales,
                "revenue": float(reg.revenue) if reg.revenue else 0.0
            }
            for reg in by_register
        ]
        
        response = jsonify({
            "status": "ok",
            "date": date_str,
            "total_sales": total_sales,
            "total_revenue": float(total_revenue),
            "by_payment_method": by_payment_method,
            "by_register": by_register_list
        })
        log_api_access('/sales/summary', 'GET', 200)
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/operational/sales/summary: {e}", exc_info=True)
        log_api_access('/sales/summary', 'GET', 500)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


@operational_api.route('/products/ranking', methods=['GET'])
def products_ranking():
    """
    Endpoint: Ranking de productos del día
    """
    auth_check = require_internal_api_key()
    if auth_check:
        log_api_access('/products/ranking', 'GET', 401)
        return auth_check
    
    try:
        date_str = request.args.get('date')
        limit = request.args.get('limit', type=int) or 10
        
        target_date = parse_date(date_str)
        date_str = target_date.strftime('%Y-%m-%d')
        
        sales_ids = db.session.query(PosSale.id).filter(
            PosSale.shift_date == date_str
        ).subquery()
        
        ranking = db.session.query(
            PosSaleItem.product_name,
            func.sum(PosSaleItem.quantity).label('quantity_sold'),
            func.sum(PosSaleItem.subtotal).label('revenue')
        ).join(
            sales_ids, PosSaleItem.sale_id == sales_ids.c.id
        ).group_by(
            PosSaleItem.product_name
        ).order_by(
            func.sum(PosSaleItem.quantity).desc()
        ).limit(limit).all()
        
        items = [
            {
                "product_name": item.product_name,
                "quantity_sold": int(item.quantity_sold) if item.quantity_sold else 0,
                "revenue": float(item.revenue) if item.revenue else 0.0
            }
            for item in ranking
        ]
        
        response = jsonify({
            "status": "ok",
            "date": date_str,
            "limit": limit,
            "items": items
        })
        log_api_access('/products/ranking', 'GET', 200)
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/operational/products/ranking: {e}", exc_info=True)
        log_api_access('/products/ranking', 'GET', 500)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


@operational_api.route('/deliveries/summary', methods=['GET'])
def deliveries_summary():
    """
    Endpoint: Resumen de entregas y bartenders
    """
    auth_check = require_internal_api_key()
    if auth_check:
        log_api_access('/deliveries/summary', 'GET', 401)
        return auth_check
    
    try:
        date_str = request.args.get('date')
        target_date = parse_date(date_str)
        date_str = target_date.strftime('%Y-%m-%d')
        
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        deliveries_query = Delivery.query.filter(
            and_(
                Delivery.timestamp >= start_datetime,
                Delivery.timestamp <= end_datetime
            )
        )
        
        by_bartender = db.session.query(
            Delivery.bartender,
            func.count(Delivery.id).label('total_deliveries'),
            func.sum(Delivery.qty).label('items_delivered')
        ).filter(
            and_(
                Delivery.timestamp >= start_datetime,
                Delivery.timestamp <= end_datetime
            )
        ).group_by(
            Delivery.bartender
        ).all()
        
        by_bartender_list = [
            {
                "bartender_id": None,
                "bartender_name": bartender.bartender,
                "total_deliveries": bartender.total_deliveries,
                "items_delivered": int(bartender.items_delivered) if bartender.items_delivered else 0
            }
            for bartender in by_bartender
        ]
        
        response = jsonify({
            "status": "ok",
            "date": date_str,
            "by_bartender": by_bartender_list
        })
        log_api_access('/deliveries/summary', 'GET', 200)
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/operational/deliveries/summary: {e}", exc_info=True)
        log_api_access('/deliveries/summary', 'GET', 500)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


@operational_api.route('/leaks/today', methods=['GET'])
def leaks_today():
    """
    Endpoint: Fugas / Inconsistencias antifraude del día
    """
    auth_check = require_internal_api_key()
    if auth_check:
        log_api_access('/leaks/today', 'GET', 401)
        return auth_check
    
    try:
        date_str = request.args.get('date')
        target_date = parse_date(date_str)
        date_str = target_date.strftime('%Y-%m-%d')
        
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        fraud_query = FraudAttempt.query.filter(
            and_(
                FraudAttempt.timestamp >= start_datetime,
                FraudAttempt.timestamp <= end_datetime
            )
        )
        
        total_suspect_tickets = fraud_query.count()
        
        confirmed_leaks = fraud_query.filter(
            FraudAttempt.authorized == False
        ).count()
        
        suspect_frauds = fraud_query.all()
        
        details = []
        estimated_loss = 0.0
        
        for fraud in suspect_frauds:
            if not fraud.authorized:
                status = "confirmed"
            else:
                status = "suspect"
            
            details.append({
                "ticket": fraud.sale_id,
                "reason": fraud.fraud_type,
                "bartender": fraud.bartender,
                "status": status
            })
        
        response = jsonify({
            "status": "ok",
            "date": date_str,
            "total_suspect_tickets": total_suspect_tickets,
            "total_confirmed_leaks": confirmed_leaks,
            "estimated_loss": estimated_loss,
            "details": details
        })
        log_api_access('/leaks/today', 'GET', 200)
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/operational/leaks/today: {e}", exc_info=True)
        log_api_access('/leaks/today', 'GET', 500)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


@operational_api.route('/summary', methods=['GET'])
def operational_summary():
    """
    Endpoint: Estado operativo del día (resumen global)
    Combina ventas, ranking, entregas y antifugas
    """
    auth_check = require_internal_api_key()
    if auth_check:
        log_api_access('/summary', 'GET', 401)
        return auth_check
    
    try:
        date_str = request.args.get('date')
        target_date = parse_date(date_str)
        date_str = target_date.strftime('%Y-%m-%d')
        
        sales_query = PosSale.query.filter(PosSale.shift_date == date_str)
        total_sales = sales_query.count()
        total_revenue = db.session.query(
            func.sum(PosSale.total_amount)
        ).filter(PosSale.shift_date == date_str).scalar() or 0.0
        
        payment_methods = db.session.query(
            func.sum(PosSale.payment_cash).label('cash'),
            func.sum(PosSale.payment_debit).label('debit'),
            func.sum(PosSale.payment_credit).label('credit')
        ).filter(PosSale.shift_date == date_str).first()
        
        by_payment_method = {
            "cash": float(payment_methods.cash) if payment_methods and payment_methods.cash else 0.0,
            "debit": float(payment_methods.debit) if payment_methods and payment_methods.debit else 0.0,
            "credit": float(payment_methods.credit) if payment_methods and payment_methods.credit else 0.0,
            "transfer": 0.0,
            "other": 0.0
        }
        
        sales_ids = db.session.query(PosSale.id).filter(
            PosSale.shift_date == date_str
        ).subquery()
        
        ranking = db.session.query(
            PosSaleItem.product_name,
            func.sum(PosSaleItem.quantity).label('quantity_sold'),
            func.sum(PosSaleItem.subtotal).label('revenue')
        ).join(
            sales_ids, PosSaleItem.sale_id == sales_ids.c.id
        ).group_by(
            PosSaleItem.product_name
        ).order_by(
            func.sum(PosSaleItem.quantity).desc()
        ).limit(10).all()
        
        top_products = [
            {
                "product_name": item.product_name,
                "quantity_sold": int(item.quantity_sold) if item.quantity_sold else 0,
                "revenue": float(item.revenue) if item.revenue else 0.0
            }
            for item in ranking
        ]
        
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        by_bartender = db.session.query(
            Delivery.bartender,
            func.count(Delivery.id).label('total_deliveries'),
            func.sum(Delivery.qty).label('items_delivered')
        ).filter(
            and_(
                Delivery.timestamp >= start_datetime,
                Delivery.timestamp <= end_datetime
            )
        ).group_by(
            Delivery.bartender
        ).all()
        
        by_bartender_list = [
            {
                "bartender_id": None,
                "bartender_name": bartender.bartender,
                "total_deliveries": bartender.total_deliveries,
                "items_delivered": int(bartender.items_delivered) if bartender.items_delivered else 0
            }
            for bartender in by_bartender
        ]
        
        fraud_query = FraudAttempt.query.filter(
            and_(
                FraudAttempt.timestamp >= start_datetime,
                FraudAttempt.timestamp <= end_datetime
            )
        )
        
        total_suspect_tickets = fraud_query.count()
        confirmed_leaks = fraud_query.filter(
            FraudAttempt.authorized == False
        ).count()
        
        response = jsonify({
            "status": "ok",
            "date": date_str,
            "sales": {
                "total_sales": total_sales,
                "total_revenue": float(total_revenue),
                "by_payment_method": by_payment_method
            },
            "products": {
                "top": top_products
            },
            "deliveries": {
                "by_bartender": by_bartender_list
            },
            "leaks": {
                "total_suspect_tickets": total_suspect_tickets,
                "total_confirmed_leaks": confirmed_leaks,
                "estimated_loss": 0.0
            }
        })
        log_api_access('/summary', 'GET', 200)
        return response, 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/operational/summary: {e}", exc_info=True)
        log_api_access('/summary', 'GET', 500)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


