"""
Helper para estadísticas avanzadas de ventas
Calcula métricas y tendencias para el dashboard
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def calculate_sales_statistics(sales_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula estadísticas avanzadas a partir de datos de ventas
    OPTIMIZADO: Usa consultas SQL directas en lugar de procesar listas en memoria
    
    Args:
        sales_data: Datos de ventas agrupados por caja (de register_sales_monitor)
        
    Returns:
        Dict con estadísticas calculadas
    """
    try:
        registers = sales_data.get('registers', {})
        summary = sales_data.get('summary', {})
        
        # Si no hay ventas, retornar vacío
        if summary.get('total_sales', 0) == 0:
            return {
                'hourly_trends': {},
                'payment_method_distribution': {},
                'average_sale_amount': 0,
                'top_products': [],
                'sales_velocity': {},
                'register_performance': {}
            }
            
        # Obtener fecha/turno del summary para filtrar queries
        shift_date = summary.get('shift_date')
        opened_at = summary.get('opened_at')
        
        # Importar modelos necesarios
        from app.models import PosSale, PosSaleItem, db
        from sqlalchemy import func, extract, desc
        
        # Construir filtro base
        base_query = PosSale.query
        if opened_at:
            try:
                if isinstance(opened_at, str):
                    opened_dt = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                    if opened_dt.tzinfo:
                        opened_dt = opened_dt.replace(tzinfo=None)
                    base_query = base_query.filter(PosSale.created_at >= opened_dt)
            except:
                if shift_date:
                    base_query = base_query.filter(PosSale.shift_date == shift_date)
        elif shift_date:
            base_query = base_query.filter(PosSale.shift_date == shift_date)
            
        # 1. Tendencias por hora (SQL)
        # SQLite: strftime('%H', created_at)
        # PostgreSQL: extract(hour from created_at)
        # Asumimos SQLite por ahora, ajustar si es Postgres
        try:
            # Intento genérico con extract (funciona en ambos usualmente)
            hourly_stats = db.session.query(
                extract('hour', PosSale.created_at).label('hour'),
                func.count(PosSale.id).label('count'),
                func.sum(PosSale.total_amount).label('amount')
            ).filter(
                PosSale.id.in_(base_query.with_entities(PosSale.id))
            ).group_by('hour').all()
            
            hourly_sales = defaultdict(lambda: {'count': 0, 'amount': 0.0})
            for stat in hourly_stats:
                hour = int(stat.hour)
                hourly_sales[hour]['count'] = stat.count
                hourly_sales[hour]['amount'] = float(stat.amount or 0)
        except Exception as e:
            logger.error(f"Error calculando tendencias horarias: {e}")
            hourly_sales = {}
        
        # 2. Distribución de métodos de pago (Usar datos ya calculados en summary)
        payment_distribution = {
            'cash': float(summary.get('total_cash', 0) or 0),
            'debit': float(summary.get('total_debit', 0) or 0),
            'credit': float(summary.get('total_credit', 0) or 0),
            'other': 0.0
        }
        
        total_payments = sum(payment_distribution.values())
        if total_payments > 0:
            payment_distribution['cash_percent'] = (payment_distribution['cash'] / total_payments) * 100
            payment_distribution['debit_percent'] = (payment_distribution['debit'] / total_payments) * 100
            payment_distribution['credit_percent'] = (payment_distribution['credit'] / total_payments) * 100
        
        # 3. Monto promedio por venta
        total_sales = summary.get('total_sales', 0)
        total_amount = float(summary.get('total_amount', 0) or 0)
        average_sale = total_amount / total_sales if total_sales > 0 else 0
        
        # 4. Productos más vendidos (Top 10) - SQL Query
        try:
            top_products_query = db.session.query(
                PosSaleItem.product_name,
                PosSaleItem.product_id,
                func.sum(PosSaleItem.quantity).label('total_qty'),
                func.sum(PosSaleItem.subtotal).label('total_amt')
            ).join(PosSale).filter(
                PosSale.id.in_(base_query.with_entities(PosSale.id))
            ).group_by(
                PosSaleItem.product_name, 
                PosSaleItem.product_id
            ).order_by(desc('total_qty')).limit(10).all()
            
            top_products = []
            for prod in top_products_query:
                top_products.append({
                    'name': prod.product_name,
                    'id': prod.product_id,
                    'count': int(prod.total_qty),
                    'amount': float(prod.total_amt or 0)
                })
        except Exception as e:
            logger.error(f"Error calculando top productos: {e}")
            top_products = []
        
        # 5. Velocidad de ventas
        sales_velocity = {}
        if total_sales > 0:
            try:
                if opened_at:
                    if isinstance(opened_at, str):
                        opened_dt = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                        if opened_dt.tzinfo:
                            opened_dt = opened_dt.replace(tzinfo=None)
                    else:
                        opened_dt = opened_at
                        
                    now = datetime.now()
                    hours_elapsed = max((now - opened_dt).total_seconds() / 3600, 0.1)
                    
                    sales_velocity = {
                        'sales_per_hour': total_sales / hours_elapsed,
                        'amount_per_hour': total_amount / hours_elapsed,
                        'hours_elapsed': hours_elapsed
                    }
            except:
                pass
        
        # 6. Rendimiento por caja (Usar datos ya calculados en registers)
        register_performance = {}
        for register_id, reg_data in registers.items():
            reg_total_sales = reg_data.get('total_sales', 0)
            reg_total_amount = float(reg_data.get('total_amount', 0) or 0)
            reg_avg = reg_total_amount / reg_total_sales if reg_total_sales > 0 else 0
            
            register_performance[register_id] = {
                'register_name': reg_data.get('register_name', f'Caja {register_id}'),
                'total_sales': reg_total_sales,
                'total_amount': reg_total_amount,
                'average_sale': reg_avg,
                'percentage_of_total': (reg_total_amount / total_amount * 100) if total_amount > 0 else 0
            }
        
        return {
            'hourly_trends': dict(hourly_sales),
            'payment_method_distribution': payment_distribution,
            'average_sale_amount': average_sale,
            'top_products': top_products,
            'sales_velocity': sales_velocity,
            'register_performance': register_performance,
            'total_sales': total_sales,
            'total_amount': total_amount
        }
        
    except Exception as e:
        logger.error(f"Error al calcular estadísticas: {e}", exc_info=True)
        return {
            'hourly_trends': {},
            'payment_method_distribution': {},
            'average_sale_amount': 0,
            'top_products': [],
            'sales_velocity': {},
            'register_performance': {},
            'error': str(e)
        }







