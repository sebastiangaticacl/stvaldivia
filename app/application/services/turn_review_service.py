"""
Servicio de Aplicación: Revisión de Turnos POS
Consolida y analiza datos de cierres de caja y ventas del turno
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from flask import current_app
from decimal import Decimal

from app.models import db, RegisterClose, PosSale, PosSaleItem
from app.infrastructure.clients.pos_api_client import PhpPosApiClient


class TurnReviewService:
    """
    Servicio para revisión y análisis de turnos POS.
    Consolida datos de cierres de caja, ventas y genera estadísticas.
    """
    
    def __init__(self, pos_client=None):
        """
        Inicializa el servicio de revisión de turnos.
        
        Args:
            pos_client: Cliente de API POS (opcional)
        """
        self.pos_client = pos_client or PhpPosApiClient()
    
    def get_turn_review_summary(self, shift_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene un resumen consolidado del turno para revisión.
        
        Args:
            shift_date: Fecha del turno (formato YYYY-MM-DD). Si es None, usa la fecha actual.
            
        Returns:
            dict: Resumen completo del turno con estadísticas consolidadas
        """
        try:
            if not shift_date:
                shift_date = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener todos los cierres del turno
            closes = RegisterClose.query.filter(
                RegisterClose.shift_date == shift_date
            ).order_by(RegisterClose.closed_at.desc()).all()
            
            # Calcular totales consolidados
            total_expected_cash = Decimal('0.0')
            total_expected_debit = Decimal('0.0')
            total_expected_credit = Decimal('0.0')
            total_actual_cash = Decimal('0.0')
            total_actual_debit = Decimal('0.0')
            total_actual_credit = Decimal('0.0')
            total_sales_count = 0
            total_sales_amount = Decimal('0.0')
            
            closes_by_status = {
                'balanced': [],
                'pending': [],
                'resolved': []
            }
            
            closes_by_register = {}
            
            for close in closes:
                # Totales esperados
                total_expected_cash += Decimal(str(close.expected_cash or 0))
                total_expected_debit += Decimal(str(close.expected_debit or 0))
                total_expected_credit += Decimal(str(close.expected_credit or 0))
                
                # Totales reales
                total_actual_cash += Decimal(str(close.actual_cash or 0))
                total_actual_debit += Decimal(str(close.actual_debit or 0))
                total_actual_credit += Decimal(str(close.actual_credit or 0))
                
                # Estadísticas
                total_sales_count += close.total_sales or 0
                total_sales_amount += Decimal(str(close.total_amount or 0))
                
                # Agrupar por estado
                status = close.status or 'pending'
                closes_by_status[status].append(close.to_dict())
                
                # Agrupar por caja
                register_id = close.register_id
                if register_id not in closes_by_register:
                    closes_by_register[register_id] = {
                        'register_id': register_id,
                        'register_name': close.register_name,
                        'closes': [],
                        'total_sales': 0,
                        'total_amount': Decimal('0.0'),
                        'total_difference': Decimal('0.0')
                    }
                
                closes_by_register[register_id]['closes'].append(close.to_dict())
                closes_by_register[register_id]['total_sales'] += close.total_sales or 0
                closes_by_register[register_id]['total_amount'] += Decimal(str(close.total_amount or 0))
                closes_by_register[register_id]['total_difference'] += Decimal(str(close.difference_total or 0))
            
            # Convertir Decimal a float para JSON
            def decimal_to_float(value):
                return float(value) if isinstance(value, Decimal) else value
            
            return {
                'shift_date': shift_date,
                'summary': {
                    'total_closes': len(closes),
                    'total_expected_cash': decimal_to_float(total_expected_cash),
                    'total_expected_debit': decimal_to_float(total_expected_debit),
                    'total_expected_credit': decimal_to_float(total_expected_credit),
                    'total_actual_cash': decimal_to_float(total_actual_cash),
                    'total_actual_debit': decimal_to_float(total_actual_debit),
                    'total_actual_credit': decimal_to_float(total_actual_credit),
                    'total_expected': decimal_to_float(total_expected_cash + total_expected_debit + total_expected_credit),
                    'total_actual': decimal_to_float(total_actual_cash + total_actual_debit + total_actual_credit),
                    'total_difference': decimal_to_float(
                        (total_actual_cash + total_actual_debit + total_actual_credit) - 
                        (total_expected_cash + total_expected_debit + total_expected_credit)
                    ),
                    'total_sales': total_sales_count,
                    'total_sales_amount': decimal_to_float(total_sales_amount),
                    'avg_sale_amount': decimal_to_float(total_sales_amount / total_sales_count) if total_sales_count > 0 else 0.0
                },
                'status_summary': {
                    'balanced': len(closes_by_status['balanced']),
                    'pending': len(closes_by_status['pending']),
                    'resolved': len(closes_by_status['resolved'])
                },
                'closes_by_status': closes_by_status,
                'closes_by_register': {
                    reg_id: {
                        **reg_data,
                        'total_amount': decimal_to_float(reg_data['total_amount']),
                        'total_difference': decimal_to_float(reg_data['total_difference'])
                    }
                    for reg_id, reg_data in closes_by_register.items()
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de revisión de turno: {e}", exc_info=True)
            return {
                'shift_date': shift_date or datetime.now().strftime('%Y-%m-%d'),
                'summary': {},
                'status_summary': {'balanced': 0, 'pending': 0, 'resolved': 0},
                'closes_by_status': {'balanced': [], 'pending': [], 'resolved': []},
                'closes_by_register': {},
                'error': str(e)
            }
    
    def get_turn_rankings(self, shift_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene rankings del turno (vendedores, productos, cajas).
        
        Args:
            shift_date: Fecha del turno (formato YYYY-MM-DD). Si es None, usa la fecha actual.
            
        Returns:
            dict: Rankings de vendedores, productos y cajas
        """
        try:
            if not shift_date:
                shift_date = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener todas las ventas del turno desde la base de datos
            # Usar shift_date que es un string YYYY-MM-DD
            sales = PosSale.query.filter(
                PosSale.shift_date == shift_date
            ).all()
            
            # Contadores para rankings
            employees_sales = defaultdict(lambda: {'name': '', 'sales_count': 0, 'total_amount': Decimal('0.0')})
            products_sales = defaultdict(lambda: {'name': '', 'quantity': 0, 'total_amount': Decimal('0.0')})
            registers_sales = defaultdict(lambda: {'name': '', 'sales_count': 0, 'total_amount': Decimal('0.0')})
            
            # Procesar ventas
            for sale in sales:
                # Ranking de empleados
                if sale.employee_id:
                    emp_key = sale.employee_id
                    if emp_key not in employees_sales or not employees_sales[emp_key]['name']:
                        employees_sales[emp_key]['name'] = sale.employee_name or f'Empleado {emp_key}'
                    employees_sales[emp_key]['sales_count'] += 1
                    employees_sales[emp_key]['total_amount'] += Decimal(str(sale.total_amount or 0))
                
                # Ranking de cajas
                if sale.register_id:
                    reg_key = sale.register_id
                    if reg_key not in registers_sales or not registers_sales[reg_key]['name']:
                        registers_sales[reg_key]['name'] = sale.register_name or f'Caja {reg_key}'
                    registers_sales[reg_key]['sales_count'] += 1
                    registers_sales[reg_key]['total_amount'] += Decimal(str(sale.total_amount or 0))
                
                # Ranking de productos (desde items)
                sale_items = PosSaleItem.query.filter_by(sale_id=sale.id).all()
                for item in sale_items:
                    product_name = item.product_name or 'Producto sin nombre'
                    products_sales[product_name]['name'] = product_name
                    products_sales[product_name]['quantity'] += item.quantity or 0
                    products_sales[product_name]['total_amount'] += Decimal(str(item.subtotal or 0))
            
            # Convertir a listas ordenadas
            def decimal_to_float(value):
                return float(value) if isinstance(value, Decimal) else value
            
            top_employees_by_sales = sorted(
                [
                    {
                        'employee_id': emp_id,
                        'name': data['name'],
                        'sales_count': data['sales_count'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_amount': decimal_to_float(data['total_amount'] / data['sales_count']) if data['sales_count'] > 0 else 0.0
                    }
                    for emp_id, data in employees_sales.items()
                ],
                key=lambda x: x['sales_count'],
                reverse=True
            )[:10]
            
            top_employees_by_amount = sorted(
                [
                    {
                        'employee_id': emp_id,
                        'name': data['name'],
                        'sales_count': data['sales_count'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_amount': decimal_to_float(data['total_amount'] / data['sales_count']) if data['sales_count'] > 0 else 0.0
                    }
                    for emp_id, data in employees_sales.items()
                ],
                key=lambda x: x['total_amount'],
                reverse=True
            )[:10]
            
            top_products_by_quantity = sorted(
                [
                    {
                        'name': name,
                        'quantity': data['quantity'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_price': decimal_to_float(data['total_amount'] / data['quantity']) if data['quantity'] > 0 else 0.0
                    }
                    for name, data in products_sales.items()
                ],
                key=lambda x: x['quantity'],
                reverse=True
            )[:10]
            
            top_products_by_amount = sorted(
                [
                    {
                        'name': name,
                        'quantity': data['quantity'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_price': decimal_to_float(data['total_amount'] / data['quantity']) if data['quantity'] > 0 else 0.0
                    }
                    for name, data in products_sales.items()
                ],
                key=lambda x: x['total_amount'],
                reverse=True
            )[:10]
            
            top_registers_by_sales = sorted(
                [
                    {
                        'register_id': reg_id,
                        'name': data['name'],
                        'sales_count': data['sales_count'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_amount': decimal_to_float(data['total_amount'] / data['sales_count']) if data['sales_count'] > 0 else 0.0
                    }
                    for reg_id, data in registers_sales.items()
                ],
                key=lambda x: x['sales_count'],
                reverse=True
            )[:10]
            
            top_registers_by_amount = sorted(
                [
                    {
                        'register_id': reg_id,
                        'name': data['name'],
                        'sales_count': data['sales_count'],
                        'total_amount': decimal_to_float(data['total_amount']),
                        'avg_amount': decimal_to_float(data['total_amount'] / data['sales_count']) if data['sales_count'] > 0 else 0.0
                    }
                    for reg_id, data in registers_sales.items()
                ],
                key=lambda x: x['total_amount'],
                reverse=True
            )[:10]
            
            return {
                'shift_date': shift_date,
                'top_employees': {
                    'by_sales_count': top_employees_by_sales,
                    'by_amount': top_employees_by_amount
                },
                'top_products': {
                    'by_quantity': top_products_by_quantity,
                    'by_amount': top_products_by_amount
                },
                'top_registers': {
                    'by_sales_count': top_registers_by_sales,
                    'by_amount': top_registers_by_amount
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener rankings del turno: {e}", exc_info=True)
            return {
                'shift_date': shift_date or datetime.now().strftime('%Y-%m-%d'),
                'top_employees': {'by_sales_count': [], 'by_amount': []},
                'top_products': {'by_quantity': [], 'by_amount': []},
                'top_registers': {'by_sales_count': [], 'by_amount': []},
                'error': str(e)
            }
    
    def get_stock_analysis(self, shift_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene análisis de stock del turno (productos vendidos).
        Por ahora retorna productos vendidos. Se puede expandir con inventario inicial/final.
        
        Args:
            shift_date: Fecha del turno (formato YYYY-MM-DD). Si es None, usa la fecha actual.
            
        Returns:
            dict: Análisis de productos vendidos durante el turno
        """
        try:
            if not shift_date:
                shift_date = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener todos los items vendidos en el turno
            sales = PosSale.query.filter(
                PosSale.shift_date == shift_date
            ).all()
            
            products_sold = defaultdict(lambda: {
                'name': '',
                'quantity': 0,
                'total_amount': Decimal('0.0'),
                'sales_count': 0
            })
            
            for sale in sales:
                sale_items = PosSaleItem.query.filter_by(sale_id=sale.id).all()
                for item in sale_items:
                    product_name = item.product_name or 'Producto sin nombre'
                    products_sold[product_name]['name'] = product_name
                    products_sold[product_name]['quantity'] += item.quantity or 0
                    products_sold[product_name]['total_amount'] += Decimal(str(item.subtotal or 0))
                    products_sold[product_name]['sales_count'] += 1
            
            # Convertir a lista
            def decimal_to_float(value):
                return float(value) if isinstance(value, Decimal) else value
            
            products_list = [
                {
                    'name': name,
                    'quantity': data['quantity'],
                    'total_amount': decimal_to_float(data['total_amount']),
                    'sales_count': data['sales_count'],
                    'avg_price': decimal_to_float(data['total_amount'] / data['quantity']) if data['quantity'] > 0 else 0.0
                }
                for name, data in products_sold.items()
            ]
            
            return {
                'shift_date': shift_date,
                'total_products': len(products_list),
                'products': sorted(products_list, key=lambda x: x['quantity'], reverse=True)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener análisis de stock: {e}", exc_info=True)
            return {
                'shift_date': shift_date or datetime.now().strftime('%Y-%m-%d'),
                'total_products': 0,
                'products': [],
                'error': str(e)
            }

